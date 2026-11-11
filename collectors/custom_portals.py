"""Public-page collectors for Indian job portals.

Extraction is intentionally strict: navigation/category links are discarded. Portals
may change their internal endpoints/markup; failures are reported rather than saved as
fake jobs. No CAPTCHA/login/anti-bot bypass is attempted.
"""
from __future__ import annotations
import json, logging, re
from urllib.parse import quote_plus, urljoin, urlencode
import requests
from bs4 import BeautifulSoup
from collectors.normalization import normalize_job

log = logging.getLogger(__name__)
PORTALS = {
 "hirist":{"name":"Hirist","base":"https://www.hirist.tech","search":"https://www.hirist.tech/k/{q}-jobs?loc={loc}"},
 "shine":{"name":"Shine.com","base":"https://www.shine.com","search":"https://www.shine.com/job-search/{q}-jobs-in-{loc}"},
 "instahyre":{"name":"Instahyre","base":"https://www.instahyre.com","search":"https://www.instahyre.com/search-jobs/?q={q}&l={loc}"},
 "internshala":{"name":"Internshala","base":"https://internshala.com","search":"https://internshala.com/internships/{q}-internship-in-{loc}/"},
 # Freshersworld's old /jobs/{role}-jobs-in-{city} route returns 404; use its live
 # public freshers listing/search page and only accept individual job detail URLs.
 "freshersworld":{"name":"Freshersworld","base":"https://www.freshersworld.com","search":"https://www.freshersworld.com/new"},
}
NAV_TITLES={"job alerts","internships","search jobs","placement courses","work from home","jobs in bangalore","jobs in delhi / ncr","jobs","careers","login","register","home","view all"}
JOB_PATHS={
 "hirist":re.compile(r"/j/[^/?#]+-\d+(?:[/?#]|$)",re.I),
 "shine":re.compile(r"/jobs/[^/?#]+/[^/?#]+/\d+(?:[/?#]|$)",re.I),
 "instahyre":re.compile(r"/job-\d+-[^/?#]+",re.I),
 "internshala":re.compile(r"/internship/detail/|/internship/[^/?#]+-\d+",re.I),
 "freshersworld":re.compile(r"/jobs?/[^/?#]+-\d+(?:[/?#]|$)",re.I),
}
def _clean(v):
 if isinstance(v,dict): return v.get("name") or v.get("value") or v.get("@id")
 if isinstance(v,list): return ", ".join(str(_clean(x)) for x in v if _clean(x))
 return re.sub(r"\s+"," ",str(v or "")).strip() or None
def _jsonld_jobs(soup):
 out=[]
 for tag in soup.select('script[type="application/ld+json"]'):
  try: data=json.loads(tag.string or tag.get_text())
  except (ValueError,TypeError): continue
  stack=data if isinstance(data,list) else [data]
  while stack:
   x=stack.pop()
   if isinstance(x,list): stack.extend(x); continue
   if not isinstance(x,dict): continue
   typ=x.get("@type",[])
   if typ=="JobPosting" or (isinstance(typ,list) and "JobPosting" in typ): out.append(x)
   for k in ("@graph","itemListElement"):
    if isinstance(x.get(k),list): stack.extend(x[k])
    elif isinstance(x.get(k),dict): stack.append(x[k])
 return out
def _from_jsonld(x,portal):
 org=x.get("hiringOrganization") or {}; loc=x.get("jobLocation") or {}
 if isinstance(loc,list): loc=loc[0] if loc else {}
 addr=loc.get("address",{}) if isinstance(loc,dict) else {}
 place=", ".join(str(y) for y in (addr.get("addressLocality"),addr.get("addressRegion")) if y)
 ident=x.get("identifier"); ident=ident.get("value") if isinstance(ident,dict) else ident
 url=x.get("url") or x.get("sameAs")
 if url: url=urljoin(PORTALS[portal]["base"],str(url))
 return {"external_id":ident,"title":x.get("title"),"company":_clean(org),"location":place or _clean(loc),
 "description":x.get("description"),"job_url":url,"posted_at":x.get("datePosted"),"status":"active"}
_job_from_jsonld = _from_jsonld  # backward-compatible parser alias

def _embedded_job_records(soup, portal):
 """Extract job objects from script-embedded JSON without relying on React DOM."""
 rows=[]; seen_obj=set()
 for tag in soup.find_all("script"):
  raw=tag.string or tag.get_text()
  if not raw or len(raw)>8_000_000: continue
  candidates=[]
  try: candidates.append(json.loads(raw))
  except (ValueError,TypeError): pass
  # Next.js/JSON state scripts sometimes wrap payload in assignments.
  for match in re.finditer(r"(?:__NEXT_DATA__|__INITIAL_STATE__|__APOLLO_STATE__)\\s*=\\s*({.*?});",raw,re.S):
   try: candidates.append(json.loads(match.group(1)))
   except ValueError: pass
  stack=list(candidates)
  while stack:
   obj=stack.pop()
   if isinstance(obj,list): stack.extend(obj); continue
   if not isinstance(obj,dict): continue
   title=obj.get("title") or obj.get("jobTitle") or obj.get("designation")
   url=obj.get("job_url") or obj.get("jobUrl") or obj.get("url") or obj.get("opportunity_url") or obj.get("opportunityUrl")
   if title and url and isinstance(url,str):
    absolute=urljoin(PORTALS[portal]["base"],url)
    if JOB_PATHS[portal].search(absolute) and absolute not in seen_obj:
     seen_obj.add(absolute)
     company=obj.get("company") or obj.get("companyName") or obj.get("employer") or obj.get("hiringOrganization")
     if isinstance(company,dict): company=company.get("name") or company.get("company_name")
     loc=obj.get("location") or obj.get("locations") or obj.get("city")
     if isinstance(loc,list): loc=", ".join(map(str,loc))
     rows.append({"title":title,"company":_clean(company),"location":_clean(loc),
       "description":obj.get("description") or obj.get("jobDescription"),"job_url":absolute,
       "external_id":obj.get("id") or obj.get("jobId"),"status":"active"})
   stack.extend(v for v in obj.values() if isinstance(v,(dict,list)))
 return rows

def _fallback(soup,portal):
 rows=[]; seen=set(); pattern=JOB_PATHS[portal]
 for a in soup.find_all("a",href=True):
  href=urljoin(PORTALS[portal]["base"],a["href"]); title=_clean(a.get_text(" ",strip=True))
  if not title or title.casefold() in NAV_TITLES or len(title)<5 or len(title)>180 or not pattern.search(href): continue
  if href in seen: continue
  seen.add(href)
  card=a
  for _ in range(5):
   if card.parent: card=card.parent
  text=card.get_text(" ",strip=True)
  # Capture company/location only when explicit labeled text is present.
  company_match=re.search(r"(?:Company|Employer)\s*[:\-]\s*([^|•]+)",text,re.I)
  loc_match=re.search(r"(?:Location|Job location)\s*[:\-]\s*([^|•]+)",text,re.I)
  rows.append({"title":title,"company":company_match.group(1).strip() if company_match else None,
   "location":loc_match.group(1).strip() if loc_match else None,"job_url":href,"description":text[:2500],"status":"active"})
 return rows

def _detail_enrich(session, portal, job, timeout):
    """Fetch a public detail page once to enrich sparse search-card metadata."""
    url=job.get("job_url")
    if not url: return job
    try:
        response=session.get(url,timeout=timeout)
        if response.status_code != 200: return job
        soup=BeautifulSoup(response.text,"html.parser")
        postings=_jsonld_jobs(soup)
        if postings:
            detail=_from_jsonld(postings[0],portal)
            for field in ("title","company","location","description","posted_at","external_id"):
                if detail.get(field) and (not job.get(field) or field=="description"):
                    job[field]=detail[field]
        og=soup.find("meta",property="og:title")
        if og and og.get("content") and not job.get("title"):
            job["title"]=og["content"].strip()
        title_tag=soup.find("title")
        if title_tag and not job.get("title"):
            job["title"]=title_tag.get_text(" ",strip=True).split("|")[0].strip()
        text=soup.get_text(" ",strip=True)
        if not job.get("company"):
            # Structured company nodes first; never accept CTA/navigation labels.
            for selector in ('[data-company-name]', '.company-name', '.companyName',
                             '.employer-name', '[class*="companyName"]', '[class*="company-name"]'):
                node=soup.select_one(selector)
                candidate=(node.get("data-company-name") if node else None) or (node.get_text(" ",strip=True) if node else None)
                candidate=_clean(candidate)
                if candidate and len(candidate)<=100 and not re.search(r"\b(close|cancel|apply|save|share|login|register)\b",candidate,re.I):
                    job["company"]=candidate
                    break
            if not job.get("company"):
                m=re.search(r"(?:Company|Employer|Organization)\s*[:\-]\s*([^|•\n]{2,80})",text,re.I)
                if m:
                    candidate=_clean(m.group(1))
                    if candidate and not re.search(r"\b(close|cancel|apply|save|share|login|register)\b",candidate,re.I):
                        job["company"]=candidate[:100]
        if not job.get("location"):
            for selector in ('[data-job-location]', '.job-location', '.location', '[class*="location"]'):
                node=soup.select_one(selector)
                candidate=(node.get("data-job-location") if node else None) or (node.get_text(" ",strip=True) if node else None)
                candidate=_clean(candidate)
                if candidate and len(candidate)<=100:
                    job["location"]=candidate
                    break
            if not job.get("location"):
                m=re.search(r"(?:Location|Job location|City)\s*[:\-]\s*([^|•\n]{2,80})",text,re.I)
                if m: job["location"]=_clean(m.group(1))[:100]
        return job
    except requests.RequestException:
        return job


def _matches_requested(job, keyword, location):
    """Conservative client-side filter; avoid unrelated portal feed results."""
    title = str(job.get("title") or "").casefold()
    desc = str(job.get("description") or "").casefold()
    query = [w.casefold() for w in re.findall(r"[a-zA-Z0-9+#.]+", keyword) if len(w)>2]
    # Require at least one meaningful query token in title/description.
    if query and not any(w in title or w in desc for w in query):
        return False
    loc = (location or "").strip().casefold()
    if loc and loc not in {"india", "anywhere", "all india", "remote"}:
        jobloc = str(job.get("location") or "").casefold()
        # If a city was requested, unknown location is not safe to accept.
        if not jobloc or (loc not in jobloc and "remote" not in jobloc and "work from home" not in jobloc):
            return False
    return True

class CustomPortalCollector:
 def __init__(self,portal,keyword="software developer",location="India",max_results=50,timeout=25,session=None):
  if portal not in PORTALS: raise ValueError(f"Unsupported custom portal: {portal}")
  self.portal=portal; self.keyword=keyword; self.location=location; self.max_results=max_results; self.timeout=timeout
  self.session=session or requests.Session(); self.session.headers.update({"User-Agent":"Mozilla/5.0 (compatible; V4CareerResearch/1.0)","Accept":"text/html,application/xhtml+xml,application/json"})
  self.source_name=PORTALS[portal]["name"]; self.base_url=PORTALS[portal]["base"]
 def search_url(self):
  cfg=PORTALS[self.portal]
  q=quote_plus(self.keyword.strip().replace(" ","-")); loc=quote_plus(self.location.strip().replace(" ","-"))
  base=cfg["search"].format(q=q,loc=loc)
  if self.portal=="freshersworld":
   # Freshersworld's /new page hosts the live job feed and search form.
   return base+"?"+urlencode({"search":self.keyword.strip(),"location":self.location.strip()})
  return base
 def fetch_jobs(self):
  url=self.search_url()
  try:
   r=self.session.get(url,timeout=self.timeout)
   if r.status_code in (401,403,429): raise RuntimeError(f"{self.source_name} blocked/limited request (HTTP {r.status_code}); no bypass attempted")
   r.raise_for_status()
  except requests.RequestException as e: raise RuntimeError(f"{self.source_name} search request failed: {e}") from e
  soup=BeautifulSoup(r.text,"html.parser")
  raw=[_from_jsonld(x,self.portal) for x in _jsonld_jobs(soup)]
  if not raw: raw=_fallback(soup,self.portal)
  jobs=[]; seen=set()
  for x in raw:
   url=x.get("job_url"); title=_clean(x.get("title"))
   if not url or not title or not JOB_PATHS[self.portal].search(url): continue
   if title.casefold() in NAV_TITLES: continue
   # avoid fabricated rows: company/location may legitimately be absent, but title+detail URL must exist
   if self.portal in {"shine","internshala"}:
    x=_detail_enrich(self.session,self.portal,x,self.timeout)
   if not _matches_requested(x, self.keyword, self.location):
    log.debug("Skip %s result outside requested keyword/location: %s | %s", self.portal, x.get("title"), x.get("location"))
    continue
   try:
    j=normalize_job(x)
    if j["url_hash"] not in seen: seen.add(j["url_hash"]); jobs.append(j)
   except (ValueError,TypeError) as e: log.debug("Skip malformed %s: %s",self.portal,e)
   if len(jobs)>=self.max_results: break
  log.info("%s: %d validated job-detail records from %s",self.source_name,len(jobs),url)
  return jobs
