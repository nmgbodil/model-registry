/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { HealthComponentDetail } from './HealthComponentDetail';
/**
 * Detailed health diagnostics broken down per component.
 */
export type HealthComponentCollection = {
    components: Array<HealthComponentDetail>;
    /**
     * Timestamp when the component report was created (UTC).
     */
    generated_at: string;
    /**
     * Observation window applied to the component metrics.
     */
    window_minutes?: number;
};

