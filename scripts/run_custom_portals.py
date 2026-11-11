#!/usr/bin/env python3
"""Run V4Career custom portal collectors (Hirist, Shine, Instahyre, Internshala, Freshersworld).

Examples:
  python scripts/run_custom_portals.py --portal hirist --keyword "Python Developer" --location Chennai --max-results 20 --dry-run
  python scripts/run_custom_portals.py --portals hirist shine instahyre internshala freshersworld --dry-run
"""
from __future__ import annotations
import argparse, logging, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT/".env")
from collectors.custom_portals import PORTALS, CustomPortalCollector
from collectors.repository import save_jobs

def main():
    p=argparse.ArgumentParser(description="Collect custom portal jobs and optionally save to V4Career database")
    p.add_argument("--portal",choices=sorted(PORTALS),help="One portal")
    p.add_argument("--portals",nargs="+",choices=sorted(PORTALS),help="Several portals")
    p.add_argument("--keyword",default="software developer")
    p.add_argument("--location",default="India")
    p.add_argument("--max-results",type=int,default=30)
    p.add_argument("--timeout",type=int,default=25)
    p.add_argument("--dry-run",action="store_true")
    p.add_argument("--delay",type=float,default=3.0,help="Pause between portals (seconds)")
    args=p.parse_args()
    if not 1<=args.max_results<=200: p.error("--max-results must be 1-200")
    portals=args.portals or ([args.portal] if args.portal else list(PORTALS))
    if args.portal and args.portals: p.error("Use either --portal or --portals")
    if args.delay<0: p.error("--delay must be >= 0")
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
    print(f"Custom portal collection | keyword={args.keyword!r} | location={args.location!r} | dry_run={args.dry_run}")
    totals={"found":0,"inserted":0,"updated":0,"failed":0}
    for idx,portal in enumerate(portals):
        collector=CustomPortalCollector(portal,args.keyword,args.location,args.max_results,args.timeout)
        print(f"\n[{idx+1}/{len(portals)}] {collector.source_name}: {collector.search_url()}")
        try:
            jobs=collector.fetch_jobs(); totals["found"]+=len(jobs)
            if args.dry_run:
                print(f"DRY RUN: {len(jobs)} normalized records; database untouched")
                for job in jobs[:3]: print("  -",job["title"],"|",job.get("company"),"|",job.get("location"),"|",job["job_url"])
            else:
                result=save_jobs(collector.source_name,collector.base_url,jobs,source_type="job_website")
                totals["inserted"]+=result.get("inserted",0); totals["updated"]+=result.get("updated",0)
                print(f"Saved: found={result.get('found')} inserted={result.get('inserted')} updated={result.get('updated')}")
        except Exception as exc:
            totals["failed"]+=1; print(f"FAILED: {type(exc).__name__}: {exc}")
        if idx<len(portals)-1: time.sleep(args.delay)
    print("\nSUMMARY:",totals)
    if args.dry_run: print("Dry run: no database writes.")
if __name__=="__main__": main()
