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
 * - 'team_lead': Administrative management for their team and project collections.
 * - 'member': Contributor within permitted project and team scopes.
 * - 'viewer': Read-only observer. Cannot access admin panel, cannot upload or delete documents.
 */

export interface UserPermissions {
  // Navigation & Page Access
  canAccessAdmin: boolean;
  canAccessCollections: boolean;
  canAccessSearch: boolean;

  // Collection Operations
  canCreateCollection: boolean;
  allowedCollectionScopes: ('org' | 'team' | 'project' | 'mine')[];
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

export function canAccessAdmin(user: UserProfile | null | undefined): boolean {
  if (!user) return false;
  return (
    user.systemRole === 'owner' ||
    user.systemRole === 'admin' ||
    user.systemRole === 'team_lead' ||
    Boolean(user.isTeamLeader)
  );
}

export function canCreateCollection(user: UserProfile | null | undefined): boolean {
  if (!user) return false;
  return user.systemRole !== 'viewer';
}

export function getAllowedCollectionScopes(user: UserProfile | null | undefined): ('org' | 'team' | 'project' | 'mine')[] {
  if (!user || user.systemRole === 'viewer') {
    return [];
  }
  if (user.systemRole === 'owner' || user.systemRole === 'admin') {
    return ['org', 'team', 'project', 'mine'];
  }
  if (user.systemRole === 'team_lead' || user.isTeamLeader) {
    return ['team', 'project', 'mine'];
  }
  // Standard member: project & personal collections
  return ['project', 'mine'];
}

export function canCreateCollectionInScope(
  user: UserProfile | null | undefined,
  scope: 'org' | 'team' | 'project' | 'mine'
): boolean {
  const allowed = getAllowedCollectionScopes(user);
  return allowed.includes(scope);
}

export function canUploadToCollection(
  user: UserProfile | null | undefined,
  collection?: Collection
): boolean {
  if (!user || user.systemRole === 'viewer') return false;
  if (user.systemRole === 'owner' || user.systemRole === 'admin') return true;

  if (!collection) return true;

  if (collection.scope === 'project') {
    return true;
  }

  if (collection.scope === 'team') {
    if (user.systemRole === 'team_lead' || user.isTeamLeader) {
      return (
        !collection.teamName ||
        !user.teamName ||
        collection.teamName.toLowerCase() === user.teamName.toLowerCase()
      );
    }
    return (
      !collection.teamName ||
      !user.teamName ||
      collection.teamName.toLowerCase() === user.teamName.toLowerCase()
    );
  }

  // Org scope: owner, admin, or team lead
  return user.systemRole === 'team_lead' || Boolean(user.isTeamLeader);
}

export function canDeleteDocument(
  user: UserProfile | null | undefined,
  doc: DocumentItem,
  collection?: Collection
): boolean {
  if (!user || user.systemRole === 'viewer') return false;
  if (user.systemRole === 'owner' || user.systemRole === 'admin') return true;

  if (collection?.scope === 'project') {
    return doc.uploadedBy?.toLowerCase() === user.name.toLowerCase() || collection.createdBy.email === user.email;
  }

  if (collection?.scope === 'team') {
    if (user.systemRole === 'team_lead' || user.isTeamLeader) return true;
    return doc.uploadedBy?.toLowerCase() === user.name.toLowerCase();
  }

  return false;
}

export function canDeleteCollection(
  user: UserProfile | null | undefined,
  collection: Collection
): boolean {
  if (!user || user.systemRole === 'viewer') return false;
  if (collection.id === 'all_knowledge_base' || collection.id === 'global') return false;
  if (user.systemRole === 'owner' || user.systemRole === 'admin') return true;

  if (collection.scope === 'project') {
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

export function canManageCollectionQuota(
  user: UserProfile | null | undefined,
  collection: Collection
): boolean {
  if (!user || user.systemRole === 'viewer') return false;
  if (user.systemRole === 'owner' || user.systemRole === 'admin') return true;

  if (collection.scope === 'team' && (user.systemRole === 'team_lead' || user.isTeamLeader)) {
    return (
      !collection.teamName ||
      !user.teamName ||
      collection.teamName.toLowerCase() === user.teamName.toLowerCase()
    );
  }

  if (collection.scope === 'project') {
    return collection.createdBy.email === user.email;
  }

  return false;
}

export function getUserPermissions(user: UserProfile | null | undefined): UserPermissions {
  const allowedScopes = getAllowedCollectionScopes(user);
  return {
    canAccessAdmin: canAccessAdmin(user),
    canAccessCollections: true,
    canAccessSearch: true,
    canCreateCollection: canCreateCollection(user),
    allowedCollectionScopes: allowedScopes,
    canCreateScope: (scope: ScopeType) =>
      scope !== 'all' && allowedScopes.includes(scope as ('org' | 'team' | 'project')),
    canDeleteCollection: (col: Collection) => canDeleteCollection(user, col),
    canManageCollectionQuota: (col: Collection) => canManageCollectionQuota(user, col),
    canUploadDocument: (col?: Collection) => canUploadToCollection(user, col),
    canImportDriveDocument: (col?: Collection) => canUploadToCollection(user, col),
    canDeleteDocument: (doc: DocumentItem, col?: Collection) => canDeleteDocument(user, doc, col),
    canManageScopeAllocations: user?.systemRole === 'owner' || user?.systemRole === 'admin',
    canManageTeamAllocations: (teamId?: string) => {
      if (user?.systemRole === 'owner' || user?.systemRole === 'admin') return true;
      if (user?.systemRole === 'team_lead' && user?.teamId) {
        return !teamId || user.teamId === teamId;
      }
      return false;
    },
    canEditIngestionConfig: user?.systemRole === 'owner' || user?.systemRole === 'admin',
    canTriggerReindex: (targetScope?: string) => {
      if (user?.systemRole === 'owner' || user?.systemRole === 'admin') return true;
      if (user?.systemRole === 'team_lead') {
        return Boolean(targetScope && targetScope !== 'all');
      }
      return false;
    }
  };
}

export function isCollectionAccessible(
  user: UserProfile | null | undefined,
  collection: Collection
): boolean {
  if (!user) return collection.scope === 'org';
  if (user.systemRole === 'owner' || user.systemRole === 'admin') return true;

  if (collection.scope === 'org') return true;
  if (collection.scope === 'team') {
    if (!collection.teamName || !user.teamName) return true;
    return collection.teamName.toLowerCase() === user.teamName.toLowerCase();
  }
  if (collection.scope === 'mine') {
    return collection.createdBy.email === user.email || collection.createdBy.name === user.name;
  }
  if (collection.scope === 'project') {
    return true;
  }
  return true;
}

