/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { HealthIssue } from './HealthIssue';
import type { HealthLogReference } from './HealthLogReference';
import type { HealthMetricMap } from './HealthMetricMap';
import type { HealthStatus } from './HealthStatus';
import type { HealthTimelineEntry } from './HealthTimelineEntry';
/**
 * Detailed status, metrics, and log references for a component.
 */
export type HealthComponentDetail = {
    /**
     * Stable identifier for the component.
     */
    id: string;
    /**
     * Human readable component name.
     */
    display_name?: string;
    status: HealthStatus;
    /**
     * Timestamp when data for this component was last collected (UTC).
     */
    observed_at: string;
    /**
     * Overview of the component's responsibility.
     */
    description?: string;
    metrics?: HealthMetricMap;
    issues?: Array<HealthIssue>;
    timeline?: Array<HealthTimelineEntry>;
    logs?: Array<HealthLogReference>;
};

