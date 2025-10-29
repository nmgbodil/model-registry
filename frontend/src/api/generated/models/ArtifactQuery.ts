/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactName } from './ArtifactName';
import type { ArtifactType } from './ArtifactType';
export type ArtifactQuery = {
    name: ArtifactName;
    /**
     * Optional list of artifact types to filter results.
     */
    types?: Array<ArtifactType>;
};

