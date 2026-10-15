-- Non-personal repository seeds only. Listed before insertion. Mumbai only.
INSERT INTO public.languages(code,name) VALUES ('en','English'),('ml','Malayalam'),('hi','Hindi'),('ta','Tamil'),('ar','Arabic'),('kn','Kannada') ON CONFLICT(code) DO NOTHING;
INSERT INTO public.subscription_plans(code,name,tier,ranking_weight,price_amount,billing_interval,features) VALUES
('growth_1m','Growth - 1 month',1,0,349.00,'monthly','{"unlimited_bookings":true,"split_bill":true,"daily_ledger":true}'::jsonb),
('growth_6m','Growth - 6 months',1,0,1499.00,'semiannual','{"unlimited_bookings":true,"split_bill":true,"daily_ledger":true}'::jsonb),
('growth_12m','Growth - 12 months',1,0,1999.00,'yearly','{"unlimited_bookings":true,"split_bill":true,"daily_ledger":true}'::jsonb),
('premium_1m','Premium - 1 month',2,1,599.00,'monthly','{"unlimited_bookings":true,"split_bill":true,"daily_ledger":true,"rank_boost":true,"smart_slot_filler":true,"sms_alerts":true,"monthly_alert_cap":300}'::jsonb),
('premium_6m','Premium - 6 months',2,1,2499.00,'semiannual','{"unlimited_bookings":true,"split_bill":true,"daily_ledger":true,"rank_boost":true,"smart_slot_filler":true,"sms_alerts":true,"monthly_alert_cap":300}'::jsonb),
('premium_12m','Premium - 12 months',2,1,3499.00,'yearly','{"unlimited_bookings":true,"split_bill":true,"daily_ledger":true,"rank_boost":true,"smart_slot_filler":true,"sms_alerts":true,"monthly_alert_cap":300}'::jsonb)
ON CONFLICT(code) DO NOTHING;
