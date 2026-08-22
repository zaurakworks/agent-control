/**
 * `domain/` must not import Bun, SQLite, the filesystem, or the process
 * environment. Only pure types and functions live here.
 *
 * `LaunchPlan` is immutable: every transition returns a *new* value rather
 * than mutating the input in place. Terminal phases never transition again,
 * with one explicit exception (`succeeded`/`degraded` -> `requires-restart`
 * on a `switch-requested` event) -- see the state diagram in the Story's
 * Design Notes.
 */

import { type Fact, known, unknown } from './facts';
import type { ClientId } from './client';

export type LaunchPhase =
  | 'prepared'
  | 'awaiting-confirmation'
  | 'applying'
  | 'observing'
  | 'succeeded'
  | 'degraded'
  | 'failed'
  | 'cancelled'
  | 'requires-restart'
  | 'incomplete';

/**
 * Phases that never accept a *normal* follow-on event. `succeeded` and
 * `degraded` are listed here too even though they accept exactly one more
 * event (`switch-requested`) -- that transition is the sole, explicitly
 * modeled exception; every other event arriving in any of these phases is
 * rejected as `invalid-transition`.
 */
export const TERMINAL_PHASES: readonly LaunchPhase[] = [
  'cancelled',
  'requires-restart',
  'succeeded',
  'degraded',
  'failed',
  'incomplete',
];

export function isTerminalPhase(phase: LaunchPhase): boolean {
  return TERMINAL_PHASES.includes(phase);
}

export type ObservedOutcome = 'succeeded' | 'degraded' | 'failed' | 'incomplete';

/**
 * Binds a confirmation to exactly one plan/revision/plan-hash triple. A
 * `confirmed` event is only accepted while `plan.phase === 'awaiting-
 * confirmation'` *and* every field here matches the current plan -- this is
 * what makes confirmations impossible to replay across a changed plan, a
 * different revision or a different process (Boundaries & Constraints).
 */
export interface ConfirmationToken {
  readonly planId: string;
  readonly revisionId: string;
  readonly planHash: string;
  readonly issuedAt: string;
}

export type LaunchPlanEvent =
  | { readonly type: 'prepared-ok' }
  | { readonly type: 'prepared-failed'; readonly reason: string }
  | { readonly type: 'confirmed'; readonly token: ConfirmationToken }
  | { readonly type: 'rejected' }
  | { readonly type: 'process-started' }
  | { readonly type: 'apply-failed'; readonly reason: string }
  | { readonly type: 'observed'; readonly outcome: ObservedOutcome; readonly reason?: string }
  | { readonly type: 'switch-requested' };

/**
 * An immutable launch plan. `confirmedAt`/`failureReason`/`observedOutcome`
 * are `Fact`s (never a bare `null`) so "not yet known" is always
 * distinguishable from "known to be absent".
 */
export interface LaunchPlan {
  readonly planId: string;
  readonly operationId: string;
  readonly revisionId: string;
  readonly configName: string;
  readonly client: ClientId;
  readonly planHash: string;
  readonly phase: LaunchPhase;
  readonly createdAt: string;
  readonly confirmedAt: Fact<string>;
  /**
   * Why the plan is in its current terminal phase, when that is known --
   * covers `prepared-failed`/`apply-failed` reasons, why a plan was
   * `cancelled` (user rejection) and why a `succeeded`/`degraded` plan
   * moved to `requires-restart` (a switch was requested).
   */
  readonly failureReason: Fact<string>;
  readonly observedOutcome: Fact<ObservedOutcome>;
}

export interface CreateLaunchPlanParams {
  readonly planId: string;
  readonly operationId: string;
  readonly revisionId: string;
  readonly configName: string;
  readonly client: ClientId;
  readonly planHash: string;
  readonly createdAt: string;
}

/** Pure constructor: every new plan starts in `prepared` with nothing yet known. */
export function createLaunchPlan(params: CreateLaunchPlanParams): LaunchPlan {
  return {
    ...params,
    phase: 'prepared',
    confirmedAt: unknown('not-yet-confirmed', params.createdAt),
    failureReason: unknown('no-failure-recorded', params.createdAt),
    observedOutcome: unknown('not-yet-observed', params.createdAt),
  };
}

/**
 * `planHash` deterministically binds a confirmation to the exact
 * `(revisionId, client, preparedAt)` triple it was issued for. Not
 * cryptographically strong by design (Design Notes) -- only deterministic
 * and reasonably resistant to accidental collision between distinct
 * inputs. No Bun/Node crypto import here: `domain/` stays free of runtime
 * dependencies.
 */
export function computePlanHash(revisionId: string, client: ClientId, preparedAt: string): string {
  const input = `${revisionId} ${client} ${preparedAt}`;
  let hash = 0;
  for (let i = 0; i < input.length; i += 1) {
    hash = (Math.imul(31, hash) + input.charCodeAt(i)) | 0;
  }
  return `ph_${(hash >>> 0).toString(16)}`;
}

export function validateConfirmationToken(
  plan: LaunchPlan,
  token: ConfirmationToken,
): { readonly ok: true } | { readonly ok: false; readonly reason: string } {
  if (plan.phase !== 'awaiting-confirmation') {
    return { ok: false, reason: 'plan-not-awaiting-confirmation' };
  }
  if (token.planId !== plan.planId || token.revisionId !== plan.revisionId || token.planHash !== plan.planHash) {
    return { ok: false, reason: 'stale-confirmation-token' };
  }
  return { ok: true };
}

function withFailure(plan: LaunchPlan, phase: LaunchPhase, reason: string): LaunchPlan {
  return { ...plan, phase, failureReason: known(reason) };
}

/**
 * The only place `LaunchPlan.phase` ever changes. Pure: returns a new
 * plan value rather than mutating `plan`. See the Story's Design Notes for
 * the full state diagram this implements.
 */
export function transitionLaunchPlan(
  plan: LaunchPlan,
  event: LaunchPlanEvent,
): { readonly ok: true; readonly plan: LaunchPlan } | { readonly ok: false; readonly reason: string } {
  switch (plan.phase) {
    case 'prepared': {
      if (event.type === 'prepared-ok') {
        return { ok: true, plan: { ...plan, phase: 'awaiting-confirmation' } };
      }
      if (event.type === 'prepared-failed') {
        return { ok: true, plan: withFailure(plan, 'failed', event.reason) };
      }
      break;
    }

    case 'awaiting-confirmation': {
      if (event.type === 'confirmed') {
        const validation = validateConfirmationToken(plan, event.token);
        if (!validation.ok) {
          return { ok: false, reason: validation.reason };
        }
        return {
          ok: true,
          plan: { ...plan, phase: 'applying', confirmedAt: known(event.token.issuedAt) },
        };
      }
      if (event.type === 'rejected') {
        return { ok: true, plan: withFailure(plan, 'cancelled', 'user-rejected-confirmation') };
      }
      break;
    }

    case 'applying': {
      if (event.type === 'process-started') {
        return { ok: true, plan: { ...plan, phase: 'observing' } };
      }
      if (event.type === 'apply-failed') {
        return { ok: true, plan: withFailure(plan, 'failed', event.reason) };
      }
      break;
    }

    case 'observing': {
      if (event.type === 'observed') {
        let next: LaunchPlan = { ...plan, phase: event.outcome, observedOutcome: known(event.outcome) };
        if (event.reason !== undefined) {
          next = { ...next, failureReason: known(event.reason) };
        }
        return { ok: true, plan: next };
      }
      break;
    }

    case 'succeeded':
    case 'degraded': {
      if (event.type === 'switch-requested') {
        return { ok: true, plan: withFailure(plan, 'requires-restart', 'switch-requested-new-configuration-selected') };
      }
      break;
    }

    // 'cancelled' | 'requires-restart' | 'failed' | 'incomplete': no event
    // is ever accepted here -- fall through to the shared rejection below.
    default:
      break;
  }

  return { ok: false, reason: 'invalid-transition' };
}

/**
 * The only fields an external CLI is ever allowed to show about a launch:
 * revision, client, client version, phase, whether configuration applied
 * cleanly or degraded, and known differences/Unknowns. No task goal,
 * conversation, tool call, task progress or result field exists on this
 * type -- see Boundaries & Constraints.
 */
export interface LaunchStatus {
  readonly revisionId: string;
  readonly client: ClientId;
  readonly clientVersion: Fact<string>;
  readonly phase: LaunchPhase;
  readonly applyResult: Fact<'applied' | 'degraded'>;
  readonly knownDifferences: readonly string[];
}

function deriveApplyResult(plan: LaunchPlan): Fact<'applied' | 'degraded'> {
  if (plan.observedOutcome.kind === 'known') {
    if (plan.observedOutcome.value === 'succeeded') {
      return known('applied');
    }
    if (plan.observedOutcome.value === 'degraded') {
      return known('degraded');
    }
    return unknown(`launch-outcome-was-${plan.observedOutcome.value}`, plan.createdAt);
  }
  // Unknown<T> carries no type parameter in its shape, so it is directly
  // reusable here without fabricating a new reason/observedAt.
  return plan.observedOutcome;
}

/** Pure projection from a `LaunchPlan` (+ externally observed facts) to `LaunchStatus`. */
export function deriveLaunchStatus(
  plan: LaunchPlan,
  clientVersion: Fact<string>,
  knownDifferences: readonly string[],
): LaunchStatus {
  return {
    revisionId: plan.revisionId,
    client: plan.client,
    clientVersion,
    phase: plan.phase,
    applyResult: deriveApplyResult(plan),
    knownDifferences,
  };
}
