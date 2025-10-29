/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request activity observed within the health window.
 */
export type HealthRequestSummary = {
    /**
     * Beginning of the aggregation window (UTC).
     */
    window_start: string;
    /**
     * End of the aggregation window (UTC).
     */
    window_end: string;
    /**
     * Number of API requests served during the window.
     */
    total_requests?: number;
    /**
     * Request counts grouped by API route.
     */
    per_route?: Record<string, number>;
    /**
     * Request counts grouped by artifact type (model/dataset/code).
     */
    per_artifact_type?: Record<string, number>;
    /**
     * Distinct API clients observed in the window.
     */
    unique_clients?: number;
};

