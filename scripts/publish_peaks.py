import os,json,base64,urllib.request,urllib.parse,datetime,pathlib
key=os.environ["OCTOPUS_API_KEY"];mpan=os.environ["OCTOPUS_ELECTRICITY_MPAN"];serial=os.environ["OCTOPUS_ELECTRICITY_SERIAL"]
now=datetime.datetime.now(datetime.timezone.utc);start=now-datetime.timedelta(days=35)
url="https://api.octopus.energy/v1/electricity-meter-points/"+urllib.parse.quote(mpan)+"/meters/"+urllib.parse.quote(serial)+"/consumption/?"+urllib.parse.urlencode({"period_from":start.isoformat(),"period_to":now.isoformat(),"page_size":25000})
slots={}
while url:
 if urllib.parse.urlparse(url).hostname!="api.octopus.energy":raise ValueError("Unexpected pagination host")
 request=urllib.request.Request(url,headers={"Authorization":"Basic "+base64.b64encode((key+":").encode()).decode()})
 with urllib.request.urlopen(request,timeout=35) as r:body=json.load(r)
 for item in body.get("results",[]):
  a=datetime.datetime.fromisoformat(item["interval_start"].replace("Z","+00:00"));b=datetime.datetime.fromisoformat(item["interval_end"].replace("Z","+00:00"))
  k=float(item["consumption"])
  if (b-a).total_seconds()==1800 and k>=0:slots[a]=(b,k)
 url=body.get("next")
rows=sorted((a,b,k) for a,(b,k) in slots.items())
if not rows:raise ValueError("No valid readings")
highest=max(rows,key=lambda x:x[2]);peak24=None
for i in range(47,len(rows)):
 block=rows[i-47:i+1]
 if (block[-1][1]-block[0][0]).total_seconds()!=86400:continue
 if any(block[j][0]!=block[j-1][1] for j in range(1,48)):continue
 total=sum(x[2] for x in block)
 if peak24 is None or total>peak24[0]:peak24=(total,block[0][0],block[-1][1])
if peak24 is None:raise ValueError("No complete 24-hour window; retain last verified snapshot")
data={"status":"verified","window_days":35,"updated_at":now.isoformat(),"rolling_24h":{"kwh":round(peak24[0],1)},"half_hour":{"kwh":round(highest[2],2),"average_kw":round(highest[2]*2,2)},"source":"Octopus half-hourly import; rounded anonymous aggregates"}
pathlib.Path("data").mkdir(exist_ok=True)
pathlib.Path("data/verified-peaks.json").write_text(json.dumps(data,indent=2)+"\n")
