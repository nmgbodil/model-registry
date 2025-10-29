/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { HealthStatus } from './HealthStatus';
/**
 * Lightweight component-level status summary.
 */
export type HealthComponentBrief = {
    /**
     * Stable identifier for the component (e.g., ingest-worker, metrics).
     */
    id: string;
    /**
     * Human readable component name.
     */
    display_name?: string;
    status: HealthStatus;
    /**
     * Number of outstanding issues contributing to the status.
     */
    issue_count?: number;
    /**
     * Last significant event timestamp for the component.
     */
    last_event_at?: string;
};

