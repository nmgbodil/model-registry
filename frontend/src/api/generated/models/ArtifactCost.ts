/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Artifact Cost aggregates the total download size (in MB) required for the artifact, optionally including dependencies.
 */
export type ArtifactCost = Record<string, {
    /**
     * The standalone cost of this artifact excluding dependencies. Required when `dependency = true` in the request.
     */
    standalone_cost?: number;
    /**
     * The total cost of the artifact. When `dependency` is not set, this should return the standalone cost,
     * and when it is set, this field should return the sum of the costs of all the dependencies.
     *
     * For example:
     *
     * Artifact 1 -> Artifact 2 -> Artifact 3, Artifact 4.
     *
     * If dependency = false
     * total_cost = size(artifact_1)
     * If dependency = true
     * total_cost = size(artifact_1 + artifact_2 + artifact_3 + artifact_4)
     *
     */
    total_cost: number;
}>;
