/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactLineageEdge } from './ArtifactLineageEdge';
import type { ArtifactLineageNode } from './ArtifactLineageNode';
/**
 * Complete lineage graph for an artifact.
 */
export type ArtifactLineageGraph = {
    /**
     * Nodes participating in the lineage graph.
     */
    nodes: Array<ArtifactLineageNode>;
    /**
     * Directed edges describing lineage relationships.
     */
    edges: Array<ArtifactLineageEdge>;
};

