/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Outstanding issue or alert impacting a component.
 */
export type HealthIssue = {
    /**
     * Machine readable issue identifier.
     */
    code: string;
    /**
     * Issue severity.
     */
    severity: HealthIssue.severity;
    /**
     * Short description of the issue.
     */
    summary: string;
    /**
     * Extended diagnostic detail and suggested remediation.
     */
    details?: string;
};
export namespace HealthIssue {
    /**
     * Issue severity.
     */
    export enum severity {
        INFO = 'info',
        WARNING = 'warning',
        ERROR = 'error',
    }
}

