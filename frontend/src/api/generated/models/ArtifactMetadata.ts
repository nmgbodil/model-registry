/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactID } from './ArtifactID';
import type { ArtifactName } from './ArtifactName';
import type { ArtifactType } from './ArtifactType';
/**
 * The `name` is provided when uploading an artifact.
 *
 * The `id` is used as an internal identifier for interacting with existing artifacts and distinguishes artifacts that share a name.
 */
export type ArtifactMetadata = {
    name: ArtifactName;
    id: ArtifactID;
    type: ArtifactType;
};

