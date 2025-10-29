/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactMetadata } from './ArtifactMetadata';
import type { User } from './User';
/**
 * One entry in an artifact's audit history.
 */
export type ArtifactAuditEntry = {
    user: User;
    /**
     * Date of activity using ISO-8601 Datetime standard in UTC format.
     */
    date: string;
    artifact: ArtifactMetadata;
    action: ArtifactAuditEntry.action;
};
export namespace ArtifactAuditEntry {
    export enum action {
        CREATE = 'CREATE',
        UPDATE = 'UPDATE',
        DOWNLOAD = 'DOWNLOAD',
        RATE = 'RATE',
        AUDIT = 'AUDIT',
    }
}

