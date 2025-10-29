/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { HealthComponentBrief } from './HealthComponentBrief';
import type { HealthLogReference } from './HealthLogReference';
import type { HealthRequestSummary } from './HealthRequestSummary';
import type { HealthStatus } from './HealthStatus';
/**
 * High-level snapshot summarizing registry health and recent activity.
 */
export type HealthSummaryResponse = {
    status: HealthStatus;
    /**
     * Timestamp when the health snapshot was generated (UTC).
     */
    checked_at: string;
    /**
     * Size of the trailing observation window in minutes.
     */
    window_minutes: number;
    /**
     * Seconds the registry API has been running.
     */
    uptime_seconds?: number;
    /**
     * Running service version or git SHA when available.
     */
    version?: string;
    request_summary?: HealthRequestSummary;
    /**
     * Rollup of component status ordered by severity.
     */
    components?: Array<HealthComponentBrief>;
    /**
     * Quick links or descriptors for recent log files.
     */
    logs?: Array<HealthLogReference>;
};

