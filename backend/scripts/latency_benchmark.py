"""Reproducible localhost benchmark. Health-only mode never reads application data.

Fixture writes require the explicit flag, port 8055 and the isolated fixture sentinel.
Ten warmups per case are excluded; errors remain in the measured denominator.
"""
import argparse
import asyncio
import json
import math
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import httpx
from api_performance import metric


def summary(values):
    if not values:
        return None
    values = sorted(values)
    return {k: round(values[max(0, math.ceil(len(values)*q)-1)],3)
            for k,q in (("min",0),("p50",.5),("p95",.95),("p99",.99),("max",1))}


async def run(args):
    url = urlparse(args.base_url)
    assert url.hostname in {"localhost","127.0.0.1"}, "Only localhost is supported"
    assert args.requests >= 50 and args.warmup >= 10
    assert not args.writes or (url.port == 8055 and args.concurrency == 1 and not args.health_only)
    report = {"base_url":args.base_url,"concurrency":args.concurrency,
              "warmup_excluded_per_case":args.warmup,"samples_per_case":args.requests,
              "auth":"local synthetic Auth test double" if not args.health_only else "not used",
              "provider_calls":0,"provider_duration_ms":None,"cases":{}}
    headers = {}
    async with httpx.AsyncClient(trust_env=False,timeout=30,
            limits=httpx.Limits(max_connections=args.concurrency)) as client:
        async def measure(name, method, path, factory=None, token=None, rows=None):
            samples = []
            responses = []
            semaphore = asyncio.Semaphore(args.concurrency)
            async def one(index, warm=False):
                async with semaphore:
                    began = time.perf_counter()
                    item = {}
                    try:
                        actual_path = path if rows is None else path.format(id=rows[index].json()["id"])
                        result = await client.request(method,args.base_url+actual_path,
                            json=factory(index) if factory else None,
                            headers={**headers,**({"Authorization":"Bearer "+token} if token else {}),
                                "Idempotency-Key":f"latency-{args.run_id}-{name}-{index}"})
                        item={"status":result.status_code,"bytes":len(result.content),
                              "request_id":result.headers.get("x-request-id"),
                              "server_timing":result.headers.get("server-timing", ""),
                              "cache_reads":int(result.headers.get("x-cache-reads",0)),
                              "cache_hits":int(result.headers.get("x-cache-hits",0))}
                        if name=="create_booking":
                            responses.append(result)
                    except (httpx.HTTPError,KeyError,ValueError) as exc:
                        item={"status":"transport_error","error_type":type(exc).__name__}
                    item["client_ms"]=(time.perf_counter()-began)*1000
                    if not warm:
                        samples.append(item)
                    return item
            warmups = [await one(i,True) for i in range(args.warmup)]
            started = time.perf_counter()
            await asyncio.gather(*(one(i+args.warmup) for i in range(args.requests)))
            elapsed = time.perf_counter()-started
            errors = sum(s["status"]=="transport_error" or s["status"]>=400 for s in samples)
            reads=sum(s.get("cache_reads",0) for s in samples)
            result={"samples":len(samples),"client_ms":summary([s["client_ms"] for s in samples]),
                    "error_rate":errors/len(samples),"requests_per_second":len(samples)/elapsed,
                    "warmup_ms":summary([s["client_ms"] for s in warmups]),
                    "warmup_errors":sum(s["status"]=="transport_error" or s["status"]>=400 for s in warmups),
                    "response_bytes":summary([s["bytes"] for s in samples if "bytes" in s]),
                    "cache_hit_rate":sum(s.get("cache_hits",0) for s in samples)/reads if reads else None}
            for key in ("app","db","redis","db_acquire","external"):
                values=[v for s in samples if (v:=metric(s.get("server_timing",""),key)) is not None]
                result[key+"_ms"]=summary(values)
            result["client_minus_app_ms"]=summary([s["client_ms"]-v for s in samples
                if (v:=metric(s.get("server_timing",""),"app")) is not None])
            result["status_codes"]={str(code):sum(s["status"]==code for s in samples)
                                    for code in {s["status"] for s in samples}}
            result["observations"]=samples
            report["cases"][name]=result
            Path(args.output).parent.mkdir(parents=True,exist_ok=True)
            Path(args.output).write_text(json.dumps(report,indent=2),encoding="utf-8")
            print(name,json.dumps(result),flush=True)
            return responses
        await measure("health","GET","/health")
        await measure("health_db","GET","/health/db")
        if not args.health_only:
            assert url.port==8055, "Synthetic business traffic is restricted to isolated port 8055"
            f=json.loads(Path(args.fixture).read_text())
            assert "salon_local_test_" in f["database_url"]
            async def login(email):
                r=await client.post("http://127.0.0.1:8050/auth/v1/token?grant_type=password",
                    json={"email":email,"password":"LocalTest123!"})
                r.raise_for_status()
                return r.json()["access_token"]
            customer=await login("customer@example.com")
            owner=await login("owner@example.com")
            headers["Authorization"]="Bearer "+customer
            await measure("authenticated_read","GET","/v1/auth/me")
            await measure("search","GET","/v1/salons?search=Local")
            await measure("salon_detail","GET",f"/v1/salons/{f['salon']}")
            await measure("slots","GET",f"/v1/availability?staff_id={f['staff']}&date={f['start'][:10]}&service_ids={f['service']}")
            # Reserve a distinct fixture day so the read-only quote remains valid
            # after the write benchmark books days 0..59. Never bypass slot checks.
            quote={"salon_id":f["salon"],"staff_id":f["staff"],"service_ids":[f["service"]],
                   "start_datetime":(datetime.fromisoformat(f["start"])+timedelta(days=60)).isoformat(),
                   "payment_mode":"PAY_AT_SALON"}
            await measure("quote","POST","/v1/bookings/quote",lambda i:quote)
            if args.writes:
                start=datetime.fromisoformat(f["start"])
                def booking(i):
                    return {"salon_id":f["salon"],"staff_id":f["staff"],"service_ids":[f["service"]],
                            "start_datetime":(start+timedelta(days=i)).isoformat(),"source":"app",
                            "payment_preference":"pay_at_salon","customer_name":"Synthetic latency test"}
                bookings=await measure("create_booking","POST","/v1/bookings",booking)
                assert len(bookings)==args.warmup+args.requests and all(r.status_code==201 for r in bookings)
                await measure("collection","POST","/v1/bookings/{id}/payment",
                              lambda i:{"payment_method":"cash"},token=owner,rows=bookings)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--base-url",default="http://127.0.0.1:8055")
    p.add_argument("--health-only",action="store_true")
    p.add_argument("--writes",action="store_true")
    p.add_argument("--requests",type=int,default=50)
    p.add_argument("--warmup",type=int,default=10)
    p.add_argument("--concurrency",type=int,default=1)
    p.add_argument("--fixture",default=".artifacts/local-fixtures.json")
    p.add_argument("--run-id",default=str(time.time_ns()))
    p.add_argument("--output",required=True)
    asyncio.run(run(p.parse_args()))
