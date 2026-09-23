import type {
  SystemRole,
  UserProfile,
  ScopeType,
  Collection,
  DocumentItem
} from '../types';

/**
 * Enterprise Governance & Role-Based Access Control (RBAC)
 * 
 * Hierarchy:
 * - 'owner': Full super-admin authority across all organizations, teams, and scopes.
 * - 'admin': Full system administrator authority for quotas, collections, ingestion, and scopes.
 * - 'team_lead': Administrative management for their team collections, team quotas, and team reindexing.
 * - 'member': Read-write contributor within permitted personal and team scopes.
 * - 'viewer': Read-only observer. Cannot access admin panel (tab is completely hidden),
 *             cannot create collections, cannot upload or delete documents.
 */

export interface UserPermissions {
  // Navigation & Page Access
  canAccessAdmin: boolean;
  canAccessCollections: boolean;
  canAccessSearch: boolean;

  // Collection Operations
  canCreateCollection: boolean;
  allowedCollectionScopes: ('mine' | 'team' | 'org')[];
  canCreateScope: (scope: ScopeType) => boolean;
  canDeleteCollection: (collection: Collection) => boolean;
  canManageCollectionQuota: (collection: Collection) => boolean;

  // Document Operations
  canUploadDocument: (collection?: Collection) => boolean;
  canImportDriveDocument: (collection?: Collection) => boolean;
  canDeleteDocument: (doc: DocumentItem, collection?: Collection) => boolean;

  // System & Infrastructure Governance
  canManageScopeAllocations: boolean;
  canManageTeamAllocations: (teamId?: string) => boolean;
  canEditIngestionConfig: boolean;
  canTriggerReindex: (targetScope?: string) => boolean;
}

/**
 * Determines whether a user has administrative privileges to view or enter the Admin panel.
 * Crucial Rule: 'viewer' (and standard 'member') CANNOT see or access the admin panel at all.
 * The tab is completely hidden.
 */
export function canAccessAdmin(user: UserProfile | null | undefined): boolean {
  if (!user) return false;
  return (
    user.systemRole === 'owner' ||
    user.systemRole === 'admin' ||
    user.systemRole === 'team_lead' ||
    Boolean(user.isTeamLeader)
  );
}

/**
 * Determines whether a user can create collections in the knowledge base.
 * Crucial Rule: 'viewer' is read-only and CANNOT create collections.
 */
export function canCreateCollection(user: UserProfile | null | undefined): boolean {
  if (!user) return false;
  return user.systemRole !== 'viewer';
}

/**
 * Returns the exact collection scopes a user is permitted to create collections in.
 * - owner / admin: 'mine', 'team', 'org'
 * - team_lead: 'mine', 'team'
 * - member: 'mine' (personal only)
 * - viewer: [] (none)
 */
export function getAllowedCollectionScopes(user: UserProfile | null | undefined): ('mine' | 'team' | 'org')[] {
  if (!user || user.systemRole === 'viewer') {
    return [];
  }
  if (user.systemRole === 'owner' || user.systemRole === 'admin') {
    return ['mine', 'team', 'org'];
  }
  if (user.systemRole === 'team_lead' || user.isTeamLeader) {
    return ['mine', 'team'];
  }
  // Standard member: personal collections only
  return ['mine'];
}

/**
 * Checks if user is permitted to create a collection in the requested scope.
 */
export function canCreateCollectionInScope(
  user: UserProfile | null | undefined,
  scope: 'mine' | 'team' | 'org'
): boolean {
  const allowed = getAllowedCollectionScopes(user);
  return allowed.includes(scope);
}

/**
 * Determines whether a user can upload or import documents into a collection.
 * Crucial Rule: 'viewer' is read-only and cannot upload.
 */
export function canUploadToCollection(
  user: UserProfile | null | undefined,
  collection?: Collection
): boolean {
  if (!user || user.systemRole === 'viewer') return false;
  if (user.systemRole === 'owner' || user.systemRole === 'admin') return true;

  if (!collection) return true;

  if (collection.scope === 'mine') {
    return collection.createdBy.email === user.email;
  }

  if (collection.scope === 'team') {
    if (user.systemRole === 'team_lead' || user.isTeamLeader) {
      return (
        !collection.teamName ||
        !user.teamName ||
        collection.teamName.toLowerCase() === user.teamName.toLowerCase()
      );
    }
    // Team member
    return (
      !collection.teamName ||
      !user.teamName ||
      collection.teamName.toLowerCase() === user.teamName.toLowerCase()
    );
  }

  // Org scope: only owner, admin, or team lead
  return user.systemRole === 'team_lead' || Boolean(user.isTeamLeader);
}

/**
 * Determines whether a user can delete a document.
 */
export function canDeleteDocument(
  user: UserProfile | null | undefined,
  doc: DocumentItem,
  collection?: Collection
): boolean {
  if (!user || user.systemRole === 'viewer') return false;
  if (user.systemRole === 'owner' || user.systemRole === 'admin') return true;

  // Personal scope
  if (collection?.scope === 'mine') {
    return collection.createdBy.email === user.email;
  }

  // Team scope: team leads can delete any document in their team; members can delete only their own
  if (collection?.scope === 'team') {
    if (user.systemRole === 'team_lead' || user.isTeamLeader) return true;
    return doc.uploadedBy?.toLowerCase() === user.name.toLowerCase();
  }

  return false;
}

/**
 * Determines whether a user can delete a collection.
 */
export function canDeleteCollection(
  user: UserProfile | null | undefined,
  collection: Collection
): boolean {
  if (!user || user.systemRole === 'viewer') return false;
  if (user.systemRole === 'owner' || user.systemRole === 'admin') return true;

  if (collection.scope === 'mine') {
    return collection.createdBy.email === user.email;
  }

  if (collection.scope === 'team') {
    return (
      (user.systemRole === 'team_lead' || Boolean(user.isTeamLeader)) &&
      (!collection.teamName ||
        !user.teamName ||
        collection.teamName.toLowerCase() === user.teamName.toLowerCase())
    );
  }

  return false;
}

/**
 * Determines whether a user can manage quota allocations for a collection or team.
 */
export function canManageCollectionQuota(
  user: UserProfile | null | undefined,
  collection: Collection
): boolean {
  if (!user || user.systemRole === 'viewer' || user.systemRole === 'member') return false;
  if (user.systemRole === 'owner' || user.systemRole === 'admin') return true;

  if (collection.scope === 'team') {
    return (
      (user.systemRole === 'team_lead' || Boolean(user.isTeamLeader)) &&
      (!collection.teamName ||
        !user.teamName ||
        collection.teamName.toLowerCase() === user.teamName.toLowerCase())
    );
  }

  return false;
}

/**
 * Computes the full permissions snapshot for a user.
 */
export function getUserPermissions(user: UserProfile): UserPermissions {
  const allowedScopes = getAllowedCollectionScopes(user);
  const isAdmin = canAccessAdmin(user);
  const isSuperAdmin = user.systemRole === 'owner' || user.systemRole === 'admin';

  return {
    canAccessAdmin: isAdmin,
    canAccessCollections: true,
    canAccessSearch: true,

    canCreateCollection: canCreateCollection(user),
    allowedCollectionScopes: allowedScopes,
    canCreateScope: (scope: ScopeType) =>
      scope !== 'all' && allowedScopes.includes(scope as ('mine' | 'team' | 'org')),
    canDeleteCollection: (collection: Collection) => canDeleteCollection(user, collection),
    canManageCollectionQuota: (collection: Collection) =>
      canManageCollectionQuota(user, collection),

    canUploadDocument: (collection?: Collection) => canUploadToCollection(user, collection),
    canImportDriveDocument: (collection?: Collection) => canUploadToCollection(user, collection),
    canDeleteDocument: (doc: DocumentItem, collection?: Collection) =>
      canDeleteDocument(user, doc, collection),

    canManageScopeAllocations: isSuperAdmin,
    canManageTeamAllocations: (teamId?: string) => {
      if (isSuperAdmin) return true;
      if (user.systemRole === 'team_lead' || user.isTeamLeader) {
        return !teamId || !user.teamId || teamId === user.teamId;
      }
      return false;
    },
    canEditIngestionConfig: isSuperAdmin,
    canTriggerReindex: (_targetScope?: string) => isAdmin,
  };
}

/**
 * Future API hook: simulates or fetches permissions from an external backend API.
 * In future production environments, this can be connected directly to an API endpoint:
 *   const res = await fetch(`/api/v1/governance/permissions?userId=${user.id}`);
 *   return await res.json();
 */
export async function fetchUserPermissions(user: UserProfile): Promise<UserPermissions> {
  return Promise.resolve(getUserPermissions(user));
}
