/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Artifact } from '../models/Artifact';
import type { ArtifactAuditEntry } from '../models/ArtifactAuditEntry';
import type { ArtifactCost } from '../models/ArtifactCost';
import type { ArtifactData } from '../models/ArtifactData';
import type { ArtifactID } from '../models/ArtifactID';
import type { ArtifactLineageGraph } from '../models/ArtifactLineageGraph';
import type { ArtifactMetadata } from '../models/ArtifactMetadata';
import type { ArtifactName } from '../models/ArtifactName';
import type { ArtifactQuery } from '../models/ArtifactQuery';
import type { ArtifactRegEx } from '../models/ArtifactRegEx';
import type { ArtifactType } from '../models/ArtifactType';
import type { AuthenticationRequest } from '../models/AuthenticationRequest';
import type { AuthenticationToken } from '../models/AuthenticationToken';
import type { EnumerateOffset } from '../models/EnumerateOffset';
import type { HealthComponentCollection } from '../models/HealthComponentCollection';
import type { ModelRating } from '../models/ModelRating';
import type { SimpleLicenseCheckRequest } from '../models/SimpleLicenseCheckRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export class DefaultService {
    /**
     * Heartbeat check (BASELINE)
     * Lightweight liveness probe. Returns HTTP 200 when the registry API is reachable.
     * @returns any Service reachable.
     * @throws ApiError
     */
    public static registryHealthHeartbeat(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health',
        });
    }
    /**
     * Get component health details (NON-BASELINE)
     * Return per-component health diagnostics, including status, active issues, and log references.
     * Use this endpoint to power deeper observability dashboards or for incident debugging.
     * @returns HealthComponentCollection Component-level health detail.
     * @throws ApiError
     */
    public static registryHealthComponents({
        windowMinutes = 60,
        includeTimeline = false,
    }: {
        /**
         * Length of the trailing observation window, in minutes (5-1440). Defaults to 60.
         */
        windowMinutes?: number,
        /**
         * Set to true to include per-component activity timelines sampled across the window.
         */
        includeTimeline?: boolean,
    }): CancelablePromise<HealthComponentCollection> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health/components',
            query: {
                'windowMinutes': windowMinutes,
                'includeTimeline': includeTimeline,
            },
        });
    }
    /**
     * Get the artifacts from the registry. (BASELINE)
     * Get any artifacts fitting the query.
     * Search for artifacts satisfying the indicated query.
     *
     * If you want to enumerate all artifacts, provide an array with a single artifact_query whose name is "*".
     *
     * The response is paginated; the response header includes the offset to use in the next query.
     * @returns ArtifactMetadata List of artifacts
     * @throws ApiError
     */
    public static artifactsList({
        xAuthorization,
        requestBody,
        offset,
    }: {
        xAuthorization: AuthenticationToken,
        requestBody: Array<ArtifactQuery>,
        /**
         * Provide this for pagination. If not provided, returns the first page of results.
         */
        offset?: EnumerateOffset,
    }): CancelablePromise<Array<ArtifactMetadata>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/artifacts',
            headers: {
                'X-Authorization': xAuthorization,
            },
            query: {
                'offset': offset,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `There is missing field(s) in the artifact_query or it is formed improperly, or is invalid.`,
                403: `Authentication failed due to invalid or missing AuthenticationToken.`,
                413: `Too many artifacts returned.`,
            },
        });
    }
    /**
     * Reset the registry. (BASELINE)
     * Reset the registry to a system default state.
     * @returns any Registry is reset.
     * @throws ApiError
     */
    public static registryReset({
        xAuthorization,
    }: {
        xAuthorization: AuthenticationToken,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/reset',
            headers: {
                'X-Authorization': xAuthorization,
            },
            errors: {
                401: `You do not have permission to reset the registry.`,
                403: `Authentication failed due to invalid or missing AuthenticationToken.`,
            },
        });
    }
    /**
     * Interact with the artifact with this id. (BASELINE)
     * Return this artifact.
     * @returns Artifact Return the artifact. url is required.
     * @throws ApiError
     */
    public static artifactRetrieve({
        artifactType,
        id,
        xAuthorization,
    }: {
        /**
         * Artifact type
         */
        artifactType: ArtifactType,
        /**
         * artifact id
         */
        id: ArtifactID,
        xAuthorization: AuthenticationToken,
    }): CancelablePromise<Artifact> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/artifacts/{artifact_type}/{id}',
            path: {
                'artifact_type': artifactType,
                'id': id,
            },
            headers: {
                'X-Authorization': xAuthorization,
            },
            errors: {
                400: `There is missing field(s) in the artifact_type or artifact_id or it is formed improperly, or is invalid.`,
                403: `Authentication failed due to invalid or missing AuthenticationToken.`,
                404: `Artifact does not exist.`,
            },
        });
    }
    /**
     * Update this content of the artifact. (BASELINE)
     * The name and id must match.
     *
     * The artifact source (from artifact_data) will replace the previous contents.
     * @returns any Artifact is updated.
     * @throws ApiError
     */
    public static artifactUpdate({
        artifactType,
        id,
        xAuthorization,
        requestBody,
    }: {
        /**
         * Artifact type
         */
        artifactType: ArtifactType,
        /**
         * artifact id
         */
        id: ArtifactID,
        xAuthorization: AuthenticationToken,
        /**
         * Type of artifact to update
         */
        requestBody: Artifact,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/artifacts/{artifact_type}/{id}',
            path: {
                'artifact_type': artifactType,
                'id': id,
            },
            headers: {
                'X-Authorization': xAuthorization,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `There is missing field(s) in the artifact_type or artifact_id or it is formed improperly, or is invalid.`,
                403: `Authentication failed due to invalid or missing AuthenticationToken.`,
                404: `Artifact does not exist.`,
            },
        });
    }
    /**
     * Delete this artifact. (NON-BASELINE)
     * Delete only the artifact that matches "id". (id is a unique identifier for an artifact)
     * @returns any Artifact is deleted.
     * @throws ApiError
     */
    public static artifactDelete({
        artifactType,
        id,
        xAuthorization,
    }: {
        /**
         * Artifact type
         */
        artifactType: ArtifactType,
        /**
         * artifact id
         */
        id: ArtifactID,
        xAuthorization: AuthenticationToken,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/artifacts/{artifact_type}/{id}',
            path: {
                'artifact_type': artifactType,
                'id': id,
            },
            headers: {
                'X-Authorization': xAuthorization,
            },
            errors: {
                400: `There is missing field(s) in the artifact_type or artifact_id or invalid`,
                403: `Authentication failed due to invalid or missing AuthenticationToken.`,
                404: `Artifact does not exist.`,
            },
        });
    }
    /**
     * Register a new artifact. (BASELINE)
     * Register a new artifact by providing a downloadable source url. Artifacts may share a name with existing entries; refer to the description above to see how an id is formed for an artifact.
     * @returns Artifact Success. Check the id in the returned metadata for the official ID.
     * @throws ApiError
     */
    public static artifactCreate({
        artifactType,
        xAuthorization,
        requestBody,
    }: {
        /**
         * Type of artifact being ingested.
         */
        artifactType: ArtifactType,
        xAuthorization: AuthenticationToken,
        requestBody: ArtifactData,
    }): CancelablePromise<Artifact> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/artifact/{artifact_type}',
            path: {
                'artifact_type': artifactType,
            },
            headers: {
                'X-Authorization': xAuthorization,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `There is missing field(s) in the artifact_data or it is formed improperly (must include a single url).`,
                403: `Authentication failed due to invalid or missing AuthenticationToken.`,
                409: `Artifact exists already.`,
                424: `Artifact is not registered due to the disqualified rating.`,
            },
        });
    }
    /**
     * Get ratings for this model artifact. (BASELINE)
     * @returns ModelRating Return the rating. Only use this if each metric was computed successfully.
     * @throws ApiError
     */
    public static modelArtifactRate({
        id,
        xAuthorization,
    }: {
        id: ArtifactID,
        xAuthorization: AuthenticationToken,
    }): CancelablePromise<ModelRating> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/artifact/model/{id}/rate',
            path: {
                'id': id,
            },
            headers: {
                'X-Authorization': xAuthorization,
            },
            errors: {
                400: `There is missing field(s) in the artifact_id or it is formed improperly, or is invalid.`,
                403: `Authentication failed due to invalid or missing AuthenticationToken.`,
                404: `Artifact does not exist.`,
                500: `The artifact rating system encountered an error while computing at least one metric.`,
            },
        });
    }
    /**
     * Get the cost of an artifact (BASELINE)
     * @returns ArtifactCost Return the total cost of the artifact, and its dependencies
     * @throws ApiError
     */
    public static getArtifactCost({
        artifactType,
        id,
        xAuthorization,
        dependency = false,
    }: {
        artifactType: ArtifactType,
        id: ArtifactID,
        xAuthorization: AuthenticationToken,
        dependency?: boolean,
    }): CancelablePromise<ArtifactCost> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/artifact/{artifact_type}/{id}/cost',
            path: {
                'artifact_type': artifactType,
                'id': id,
            },
            headers: {
                'X-Authorization': xAuthorization,
            },
            query: {
                'dependency': dependency,
            },
            errors: {
                400: `There is missing field(s) in the artifact_type or artifact_id or it is formed improperly, or is invalid.`,
                403: `Authentication failed due to invalid or missing AuthenticationToken.`,
                404: `Artifact does not exist.`,
                500: `The artifact cost calculator encountered an error.`,
            },
        });
    }
    /**
     * (NON-BASELINE)
     * Create an access token.
     * @returns AuthenticationToken Return an AuthenticationToken.
     * @throws ApiError
     */
    public static createAuthToken({
        requestBody,
    }: {
        requestBody: AuthenticationRequest,
    }): CancelablePromise<AuthenticationToken> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/authenticate',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `There is missing field(s) in the AuthenticationRequest or it is formed improperly.`,
                401: `The user or password is invalid.`,
                501: `This system does not support authentication.`,
            },
        });
    }
    /**
     * List artifact metadata for this name. (NON-BASELINE)
     * Return metadata for each artifact matching this name.
     * @returns ArtifactMetadata Return artifact metadata entries that match the provided name.
     * @throws ApiError
     */
    public static artifactByNameGet({
        name,
        xAuthorization,
    }: {
        name: ArtifactName,
        xAuthorization: AuthenticationToken,
    }): CancelablePromise<Array<ArtifactMetadata>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/artifact/byName/{name}',
            path: {
                'name': name,
            },
            headers: {
                'X-Authorization': xAuthorization,
            },
            errors: {
                400: `There is missing field(s) in the artifact_name or it is formed improperly, or is invalid.`,
                403: `Authentication failed due to invalid or missing AuthenticationToken.`,
                404: `No such artifact.`,
            },
        });
    }
    /**
     * Retrieve audit entries for this artifact. (NON-BASELINE)
     * @returns ArtifactAuditEntry Return the audit trail for this artifact. (NON-BASELINE)
     * @throws ApiError
     */
    public static artifactAuditGet({
        artifactType,
        id,
        xAuthorization,
    }: {
        /**
         * Type of artifact to audit
         */
        artifactType: ArtifactType,
        /**
         * artifact id
         */
        id: ArtifactID,
        xAuthorization: AuthenticationToken,
    }): CancelablePromise<Array<ArtifactAuditEntry>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/artifact/{artifact_type}/{id}/audit',
            path: {
                'artifact_type': artifactType,
                'id': id,
            },
            headers: {
                'X-Authorization': xAuthorization,
            },
            errors: {
                400: `There is missing field(s) in the artifact_type or artifact_id or it is formed improperly, or is invalid.`,
                403: `Authentication failed due to invalid or missing AuthenticationToken.`,
                404: `Artifact does not exist.`,
            },
        });
    }
    /**
     * Retrieve the lineage graph for this artifact. (BASELINE)
     * @returns ArtifactLineageGraph Lineage graph extracted from structured metadata. (BASELINE)
     * @throws ApiError
     */
    public static artifactLineageGet({
        id,
        xAuthorization,
    }: {
        /**
         * artifact id
         */
        id: ArtifactID,
        xAuthorization: AuthenticationToken,
    }): CancelablePromise<ArtifactLineageGraph> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/artifact/model/{id}/lineage',
            path: {
                'id': id,
            },
            headers: {
                'X-Authorization': xAuthorization,
            },
            errors: {
                400: `The lineage graph cannot be computed because the artifact metadata is missing or malformed.`,
                403: `Authentication failed due to invalid or missing AuthenticationToken.`,
                404: `Artifact does not exist.`,
            },
        });
    }
    /**
     * Assess license compatibility for fine-tune and inference usage. (BASELINE)
     * @returns boolean License compatibility analysis produced successfully. (BASELINE)
     * @throws ApiError
     */
    public static artifactLicenseCheck({
        id,
        xAuthorization,
        requestBody,
    }: {
        /**
         * artifact id
         */
        id: ArtifactID,
        xAuthorization: AuthenticationToken,
        requestBody: SimpleLicenseCheckRequest,
    }): CancelablePromise<boolean> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/artifact/model/{id}/license-check',
            path: {
                'id': id,
            },
            headers: {
                'X-Authorization': xAuthorization,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `The license check request is malformed or references an unsupported usage context.`,
                403: `Authentication failed due to invalid or missing AuthenticationToken.`,
                404: `The artifact or GitHub project could not be found.`,
                502: `External license information could not be retrieved.`,
            },
        });
    }
    /**
     * Get any artifacts fitting the regular expression (BASELINE).
     * Search for an artifact using regular expression over artifact names and READMEs. This is similar to search by name.
     * @returns ArtifactMetadata Return a list of artifacts.
     * @throws ApiError
     */
    public static artifactByRegExGet({
        xAuthorization,
        requestBody,
    }: {
        xAuthorization: AuthenticationToken,
        requestBody: ArtifactRegEx,
    }): CancelablePromise<Array<ArtifactMetadata>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/artifact/byRegEx',
            headers: {
                'X-Authorization': xAuthorization,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `There is missing field(s) in the artifact_regex or it is formed improperly, or is invalid`,
                403: `Authentication failed due to invalid or missing AuthenticationToken.`,
                404: `No artifact found under this regex.`,
            },
        });
    }
    /**
     * Get the list of tracks a student has planned to implement in their code
     * @returns any Return the list of tracks the student plans to implement
     * @throws ApiError
     */
    public static getTracks(): CancelablePromise<{
        /**
         * List of tracks the student plans to implement
         */
        plannedTracks?: Array<'Performance track' | 'Access control track' | 'High assurance track' | 'Other Security track'>;
    }> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/tracks',
            errors: {
                500: `The system encountered an error while retrieving the student's track information.`,
            },
        });
    }
}
