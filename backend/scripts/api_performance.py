"""Explicit local/staging API load measurement. Production is intentionally unsupported.

Never stores JWTs or response bodies. Writes measured latency and Server-Timing metrics.
Writes require --allow-test-writes and the known disposable local fixture manifest.
"""

import argparse
import asyncio
import json
import math
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import httpx


def percentile(values, fraction):
    return sorted(values)[max(0,math.ceil(len(values)*fraction)-1)] if values else None


def metric(header, name):
    match=re.search(rf"\b{name};dur=([0-9.]+)",header)
    return float(match[1]) if match else None


async def run(args):
    target=urlparse(args.base_url)
    if target.hostname not in {"127.0.0.1","localhost"} or urlparse(args.auth_url).hostname not in {"127.0.0.1","localhost"}:
        raise ValueError("This runner is limited to the isolated localhost environment")
    fixture=json.loads(Path(args.fixture).read_text())
    cases={"health":("GET","/health",None), "readiness":("GET","/health/ready",None),
           "search":("GET","/v1/salons?search=Local",None),
           "authenticated_read":("GET","/v1/auth/me",None),
           "salon_detail":("GET",f"/v1/salons/{fixture['salon']}",None),
           "slots":("GET",f"/v1/availability?staff_id={fixture['staff']}&date={fixture['start'][:10]}&service_ids={fixture['service']}",None),
           "quote":("POST","/v1/bookings/quote",{"salon_id":fixture["salon"],"staff_id":fixture["staff"],"service_ids":[fixture["service"]],"start_datetime":fixture["start"],"payment_mode":"PAY_AT_SALON"})}
    report={"environment":"isolated_local_docker","base_url":args.base_url,"requests_per_case":args.requests,
            "concurrency":args.concurrency,"auth":"normal JWT verification, local Supabase Auth test double",
            "external_provider_calls":0,"cache_hit_rate":None,"cases":{}}
    async with httpx.AsyncClient(timeout=30,limits=httpx.Limits(max_connections=args.concurrency)) as client:
        async def login(email):
            result=await client.post(args.auth_url+"/auth/v1/token?grant_type=password",json={"email":email,"password":"LocalTest123!"})
            result.raise_for_status()
            return result.json()["access_token"]
        customer=await login("customer@example.com")
        owner=await login("owner@example.com")
        async def measure(name, method, path, body, n=None, token=customer, factory=None):
            latencies,app_durations,db_durations,query_counts=[],[],[],[]
            errors,statuses=0,{}
            cache_reads=cache_hits=0
            semaphore=asyncio.Semaphore(args.concurrency)
            async def one(i):
                nonlocal errors,cache_reads,cache_hits
                async with semaphore:
                    data=body if factory is None else factory(i)
                    started=time.perf_counter()
                    result=await client.request(method,args.base_url+path,json=data,
                        headers={"Authorization":"Bearer "+token,"Idempotency-Key":f"perf-{name}-{args.run_id}-{i}"})
                    latencies.append((time.perf_counter()-started)*1000)
                    statuses[str(result.status_code)]=statuses.get(str(result.status_code),0)+1
                    errors+=int(result.status_code>=400)
                    cache_reads+=int(result.headers.get("x-cache-reads",0))
                    cache_hits+=int(result.headers.get("x-cache-hits",0))
                    header=result.headers.get("server-timing","")
                    for metric_name,values in (("app",app_durations),("db",db_durations)):
                        value=metric(header,metric_name)
                        if value is not None:values.append(value)
                    count=re.search(r'queries;desc="(\d+)"',header)
                    if count:query_counts.append(int(count[1]))
                    return result
            await one(-1)  # separate warmup, excluded from measured samples
            latencies.clear();app_durations.clear();db_durations.clear();query_counts.clear();errors=0;statuses.clear()
            cache_reads=cache_hits=0
            started=time.perf_counter()
            responses=await asyncio.gather(*(one(i) for i in range(n or args.requests)))
            elapsed=time.perf_counter()-started
            report["cases"][name]={"samples":len(latencies),"p50_ms":round(percentile(latencies,.5),3),
                "p95_ms":round(percentile(latencies,.95),3),"p99_ms":round(percentile(latencies,.99),3),
                "error_rate":errors/len(latencies),"requests_per_second":round(len(latencies)/elapsed,2),"status_codes":statuses,
                "app_p95_ms":percentile(app_durations,.95),"database_p95_ms":percentile(db_durations,.95),
                "database_queries_mean":sum(query_counts)/len(query_counts) if query_counts else None,
                "cache_reads":cache_reads,"cache_hits":cache_hits,
                "cache_hit_rate":cache_hits/cache_reads if cache_reads else None}
            return responses
        for name,(method,path,body) in cases.items():
            await measure(name,method,path,body)
        if args.allow_test_writes:
            start=datetime.fromisoformat(fixture["start"])
            def booking(i):
                return {"salon_id":fixture["salon"],"staff_id":fixture["staff"],"service_ids":[fixture["service"]],
                    "start_datetime":(start+timedelta(days=i+10)).isoformat(),"source":"app", "payment_preference":"pay_at_salon","customer_name":"Performance test customer"}
            # 20 unique local fixture days, avoiding the legitimate one/day cap.
            responses=await measure("create_booking","POST","/v1/bookings",None,n=20,factory=booking)
            collected=[]
            for i,result in enumerate(responses):
                if result.status_code==201:
                    bid=result.json()["id"]
                    began=time.perf_counter()
                    receipt=await client.post(args.base_url+f"/v1/bookings/{bid}/payment",json={"payment_method":"cash"},headers={"Authorization":"Bearer "+owner,"Idempotency-Key":f"perf-collect-{args.run_id}-{i}"})
                    collected.append({"duration_ms":(time.perf_counter()-began)*1000,"status":receipt.status_code})
            durations=[row["duration_ms"] for row in collected]
            report["cases"]["collection"]={"samples":len(durations),"p50_ms":percentile(durations,.5),"p95_ms":percentile(durations,.95),"p99_ms":percentile(durations,.99),"error_rate":sum(row["status"]>=400 for row in collected)/len(collected) if collected else None,"concurrency":1}
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--base-url",default="http://127.0.0.1:8055")
    parser.add_argument("--auth-url",default="http://127.0.0.1:8050")
    parser.add_argument("--fixture",default=".artifacts/local-fixtures.json")
    parser.add_argument("--requests",type=int,default=50)
    parser.add_argument("--concurrency",type=int,default=5)
    parser.add_argument("--run-id",default=str(int(time.time())))
    parser.add_argument("--allow-test-writes",action="store_true")
    parser.add_argument("--output",default=".artifacts/api-performance.json")
    asyncio.run(run(parser.parse_args()))
