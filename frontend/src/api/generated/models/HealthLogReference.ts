/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Link or descriptor for logs relevant to a health component.
 */
export type HealthLogReference = {
    /**
     * Human readable log descriptor (e.g., "Ingest Worker 1").
     */
    label: string;
    /**
     * Direct link to download or tail the referenced log.
     */
    url: string;
    /**
     * Indicates whether streaming tail access is supported.
     */
    tail_available?: boolean;
    /**
     * Timestamp of the latest log entry available for this reference.
     */
    last_updated_at?: string;
};

