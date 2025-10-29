/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Time-series datapoint for a component metric.
 */
export type HealthTimelineEntry = {
    /**
     * Start timestamp of the sampled bucket (UTC).
     */
    bucket: string;
    /**
     * Observed value for the bucket (e.g., requests per minute).
     */
    value: number;
    /**
     * Unit associated with the metric value.
     */
    unit?: string;
};

