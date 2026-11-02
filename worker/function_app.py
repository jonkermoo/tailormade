"""Background worker: the crawler pipeline.

crawl_jobs (timer, every 2 hours)
    -> raw snapshot JSON to Blob Storage (container: raw-crawls)
    -> one message per job to Queue Storage (queue: jobs-to-process)
process_job (queue trigger)
    -> dedupe hash -> (next) upsert into Azure SQL, score, push live alert
"""
import json
import logging

import azure.functions as func

from crawler.normalize import dedupe_hash
from crawler.run import crawl

app = func.FunctionApp()


@app.timer_trigger(arg_name="timer", schedule="0 0 */2 * * *", run_on_startup=False)
@app.blob_output(arg_name="snapshot",
                 path="raw-crawls/{DateTime}.json",
                 connection="AzureWebJobsStorage")
@app.queue_output(arg_name="outbox",
                  queue_name="jobs-to-process",
                  connection="AzureWebJobsStorage")
def crawl_jobs(timer: func.TimerRequest,
               snapshot: func.Out[str],
               outbox: func.Out[list[str]]) -> None:
    raw, jobs = crawl()
    snapshot.set(json.dumps(raw))
    outbox.set([json.dumps(job) for job in jobs])
    logging.info("Crawl finished: %d jobs queued, %d source errors",
                 len(jobs), len(raw["errors"]))


@app.queue_trigger(arg_name="msg",
                   queue_name="jobs-to-process",
                   connection="AzureWebJobsStorage")
def process_job(msg: func.QueueMessage) -> None:
    job = json.loads(msg.get_body().decode("utf-8"))
    # Recompute rather than trust the message, so the rule lives in one place
    job["dedupe_hash"] = dedupe_hash(job["company"], job["title"], job["location"])
    logging.info("Processed %s | %s | %s -> %s",
                 job["company"], job["title"], job["location"], job["dedupe_hash"][:12])
    # TODO: upsert into jobs/job_sources (db/schema.sql), score against
    # saved_filters, and send a SignalR message for high matches.
