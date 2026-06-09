# External Runner Skill Walkthrough

This document demonstrates the skill correctly explaining process-failure and
process-success-with-issue scenarios using the tier vocabulary verbatim, per
`operator-experience.md`'s Copy and Message Guidelines.

---

## Scenario A — Process failure (HTTP endpoint unreachable)

**Operator:** "I ran `gavel oneshot run --eval my-http-eval` and it stopped early. The
terminal showed something about a 503."

**Skill (after reading the Rich panel and `run.log`):**

> This is a **process failure** — the external system did not complete. The run halted
> because `abort_on_exec_failure` is on (the default).
>
> Specifically: `process failure: endpoint returned 503`
>
> The `trace_id` for the failing invocation is `abc-123-def`. Use that to find the
> matching entry in `run.log` (it will show the full request that was attempted) and in
> `telemetry.jsonl` (it will show the HTTP span with timing).
>
> The most likely causes:
> - The endpoint URL in `config.endpoint` is wrong or the service is down.
> - The auth token in `config.auth` has expired or is missing required headers.
>
> Do you want me to check the `endpoint` and `auth` fields in your `eval_config.json`,
> or would you prefer to set `abort_on_exec_failure: false` to collect results from the
> remaining scenarios before diagnosing?

---

## Scenario B — Process failure (script exits non-zero)

**Operator:** "The run failed with something about 'script exited with code 1'. What
does that mean?"

**Skill:**

> This is a **process failure** — the script itself did not complete successfully.
> The run halted on this invocation.
>
> Specifically: `process failure: script exited with code 1`
>
> The `trace_id` for this invocation is `xyz-456-uvw`. Check `run.log` for the bounded
> stderr output captured from your script — it will show what the script printed before
> exiting. That's usually the fastest path to the root cause.
>
> If you want the run to continue past script crashes and collect results for the other
> scenarios, set `abort_on_exec_failure: false` in your `eval_config.json` under
> `test_subjects[0]`.

---

## Scenario C — Process success with internal issue (warning)

**Operator:** "The run finished but I see a warning in the logs about 'low_confidence'.
Did something go wrong?"

**Skill:**

> No crash here — this is **process success with issue**. The script ran fine and
> completed, but it flagged its own output with a low-confidence warning. The run kept
> going because `abort_on_process_error` is off (the default).
>
> Specifically: `process success with issue: low_confidence — the script ran fine and
> flagged a low-confidence result`
>
> The warning is attached to the record in `results_raw.jsonl` under `error` and
> `metadata`, and you can find it by searching for `trace_id: <the-trace-id>` in
> `run.log`. The record still counts as a processed scenario — it's not excluded from
> judging.
>
> If you want the run to stop when the script reports a problem like this, set
> `abort_on_process_error: true` in your `eval_config.json`.

---

## Scenario D — Process success with halting internal error

**Operator:** "I set `abort_on_process_error: true` and the run stopped with something
about 'validation_failed'. Is that a crash?"

**Skill:**

> No — the external system ran fine. This is **process success with issue**, and the
> run halted because you have `abort_on_process_error: true`.
>
> The service completed and returned a response, but it reported an application-level
> problem (`status: "error"` with issue code `validation_failed`) in its response
> envelope. That means the failure is inside the service's own logic, not a transport
> or process problem.
>
> Specifically: `process success with issue: validation_failed`
>
> Use `trace_id: <the-trace-id>` in `telemetry.jsonl` and `run.log` to find the exact
> invocation. The request payload that triggered the issue is also in `run.log`. You
> may want to share the `trace_id` with the team that owns the external service — they
> can use it to look up that specific call in their own logs.

---

## Key vocabulary reference

| Term used | Meaning |
|---|---|
| **process failure** | The external system did not complete — transport error, non-2xx, crash, timeout, or missing response document |
| **process success with issue** | The external system completed but its response envelope flagged a problem (`status: "error"` or non-empty `issue`) |
| `trace_id` | The correlator — always include this when relaying an issue so the operator can pivot into `telemetry.jsonl`, `run.log`, or their service's logs |
| `abort_on_exec_failure` | Controls whether a process failure halts the run (default: `true`) |
| `abort_on_process_error` | Controls whether a process-success-with-issue halts the run (default: `false`) |
