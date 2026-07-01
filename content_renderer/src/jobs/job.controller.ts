/**
 * Job controller (CR-201 / R-HARD-001).
 *
 * Handles `POST /jobs`: validates the envelope schema, checks header/body
 * consistency, accepts the job and responds `202 Accepted` quickly — WITHOUT
 * waiting for the render/callback. Internal-token authentication is applied
 * upstream as route middleware (see http/routes.ts).
 *
 * Reception is decoupled from execution (R-HARD-001):
 *   1. validate token (middleware) → headers → envelope;
 *   2. `jobService.acceptJob` validates the job_type (unknown → controlled 400,
 *      no callback) and logs `job.accepted`;
 *   3. `jobService.scheduleJobExecution` detaches render → storage → callback
 *      onto a light-weight background tick;
 *   4. respond `202` immediately.
 *
 * The render result is NO LONGER echoed in the 202 body: it is produced in the
 * background and delivered to Django via the callback. The 202 is purely an
 * acceptance acknowledgement. This removes the race with the Django
 * `ExternalJobReference` state that a synchronous callback could cause.
 */
import type { Request, Response } from 'express';

import { RENDERER_NAME, RENDERER_VERSION } from '../constants';
import type { Logger } from '../logging/logger';
import { InvalidPayloadError } from '../errors/errors';
import { enforceJobHeaderConsistency } from '../http/middleware';
import { parseJobEnvelope } from './job.schema';
import type { JobService } from './job.service';

export interface JobControllerDeps {
  jobService: JobService;
  logger: Logger;
}

export interface JobController {
  receiveJob(req: Request, res: Response): Promise<void>;
}

export function createJobController(deps: JobControllerDeps): JobController {
  const { jobService, logger } = deps;

  async function receiveJob(req: Request, res: Response): Promise<void> {
    const reqLogger: Logger = (res.locals.logger as Logger | undefined) ?? logger;

    // 1. Validate the envelope schema (CR-103).
    const parsed = parseJobEnvelope(req.body);
    if (!parsed.success) {
      const issues = parsed.error.issues.map((issue) => ({
        path: issue.path.map((segment) => String(segment)).join('.'),
        message: issue.message,
      }));
      reqLogger.warn('job.invalid_payload', { issue_count: issues.length });
      throw new InvalidPayloadError('Invalid job payload.', { issues });
    }
    const envelope = parsed.data;

    // 2. Validate header/body consistency (CR-102).
    enforceJobHeaderConsistency(req, envelope, reqLogger);

    // 3. Accept the job (CR-202). An unsupported job_type throws a controlled
    // 400 here (the job is declined — no callback). Otherwise this logs
    // `job.accepted` and returns the job-scoped execution context.
    const context = jobService.acceptJob(envelope);

    // 4. Schedule render → storage → callback on a light-weight background tick
    // and return immediately (R-HARD-001). The result is delivered to Django via
    // the callback, NOT echoed in this response.
    jobService.scheduleJobExecution(envelope, context);

    // 5. Respond 202 Accepted (acceptance acknowledgement only).
    res.status(202).json({
      status: 'accepted',
      job_id: envelope.job_id,
      workspace_id: envelope.workspace_id,
      job_type: envelope.job_type,
      entity: envelope.entity,
      metadata: {
        renderer: RENDERER_NAME,
        renderer_version: RENDERER_VERSION,
      },
    });
  }

  return { receiveJob };
}
