/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactID } from './ArtifactID';
/**
 * Directed relationship between two lineage nodes.
 */
export type ArtifactLineageEdge = {
    /**
     * Identifier of the upstream node.
     */
    from_node_artifact_id: ArtifactID;
    /**
     * Identifier of the downstream node.
     */
    to_node_artifact_id: ArtifactID;
    /**
     * Qualitative description of the edge.
     */
    relationship: string;
};

