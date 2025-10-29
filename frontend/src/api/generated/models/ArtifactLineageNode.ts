/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactID } from './ArtifactID';
/**
 * A single node in an artifact lineage graph.
 */
export type ArtifactLineageNode = {
    /**
     * Unique identifier for the node (artifact or external dependency).
     */
    artifact_id?: ArtifactID;
    /**
     * Human-readable label for the node.
     */
    name?: string;
    /**
     * Provenance for how the node was discovered.
     */
    source?: string;
    /**
     * Optional metadata captured for lineage analysis.
     */
    metadata?: Record<string, any>;
};

