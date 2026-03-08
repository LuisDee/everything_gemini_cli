/**
 * Session Aliases Library for Gemini CLI
 * Manages session aliases stored in ~/.gemini/session-aliases.json
 */

const fs = require('fs');
const path = require('path');

const {
  getGeminiDir,
  ensureDir,
  readFile,
  log
} = require('./utils');

// Aliases file path
function getAliasesPath() {
  return path.join(getGeminiDir(), 'session-aliases.json');
}

// Current alias storage format version
const ALIAS_VERSION = '1.0';

/**
 * Default aliases file structure
 */
function getDefaultAliases() {
  return {
    version: ALIAS_VERSION,
    aliases: {},
    metadata: {
      totalCount: 0,
      lastUpdated: new Date().toISOString()
    }
  };
}

/**
 * Load aliases from file
 * @returns {object} Aliases object
 */
function loadAliases() {
  const aliasesPath = getAliasesPath();

  if (!fs.existsSync(aliasesPath)) {
    return getDefaultAliases();
  }

  const content = readFile(aliasesPath);
  if (!content) {
    return getDefaultAliases();
  }

  try {
    const data = JSON.parse(content);

    if (!data.aliases || typeof data.aliases !== 'object') {
      log('[Aliases] Invalid aliases file structure, resetting');
      return getDefaultAliases();
    }

    if (!data.version) {
      data.version = ALIAS_VERSION;
    }

    if (!data.metadata) {
      data.metadata = {
        totalCount: Object.keys(data.aliases).length,
        lastUpdated: new Date().toISOString()
      };
    }

    return data;
  } catch (err) {
    log(`[Aliases] Error parsing aliases file: ${err.message}`);
    return getDefaultAliases();
  }
}

/**
 * Save aliases to file with atomic write
 * @param {object} aliases - Aliases object to save
 * @returns {boolean} Success status
 */
function saveAliases(aliases) {
  const aliasesPath = getAliasesPath();
  const tempPath = aliasesPath + '.tmp';
  const backupPath = aliasesPath + '.bak';

  try {
    aliases.metadata = {
      totalCount: Object.keys(aliases.aliases).length,
      lastUpdated: new Date().toISOString()
    };

    const content = JSON.stringify(aliases, null, 2);

    ensureDir(path.dirname(aliasesPath));

    if (fs.existsSync(aliasesPath)) {
      fs.copyFileSync(aliasesPath, backupPath);
    }

    fs.writeFileSync(tempPath, content, 'utf8');

    if (process.platform === 'win32' && fs.existsSync(aliasesPath)) {
      fs.unlinkSync(aliasesPath);
    }
    fs.renameSync(tempPath, aliasesPath);

    if (fs.existsSync(backupPath)) {
      fs.unlinkSync(backupPath);
    }

    return true;
  } catch (err) {
    log(`[Aliases] Error saving aliases: ${err.message}`);

    if (fs.existsSync(backupPath)) {
      try {
        fs.copyFileSync(backupPath, aliasesPath);
        log('[Aliases] Restored from backup');
      } catch (restoreErr) {
        log(`[Aliases] Failed to restore backup: ${restoreErr.message}`);
      }
    }

    try {
      if (fs.existsSync(tempPath)) {
        fs.unlinkSync(tempPath);
      }
    } catch {
      // Non-critical
    }

    return false;
  }
}

/**
 * Resolve an alias to get session path
 */
function resolveAlias(alias) {
  if (!alias) return null;

  if (!/^[a-zA-Z0-9_-]+$/.test(alias)) {
    return null;
  }

  const data = loadAliases();
  const aliasData = data.aliases[alias];

  if (!aliasData) {
    return null;
  }

  return {
    alias,
    sessionPath: aliasData.sessionPath,
    createdAt: aliasData.createdAt,
    title: aliasData.title || null
  };
}

/**
 * Set or update an alias for a session
 */
function setAlias(alias, sessionPath, title = null) {
  if (!alias || alias.length === 0) {
    return { success: false, error: 'Alias name cannot be empty' };
  }

  if (!sessionPath || typeof sessionPath !== 'string' || sessionPath.trim().length === 0) {
    return { success: false, error: 'Session path cannot be empty' };
  }

  if (alias.length > 128) {
    return { success: false, error: 'Alias name cannot exceed 128 characters' };
  }

  if (!/^[a-zA-Z0-9_-]+$/.test(alias)) {
    return { success: false, error: 'Alias name must contain only letters, numbers, dashes, and underscores' };
  }

  const reserved = ['list', 'help', 'remove', 'delete', 'create', 'set'];
  if (reserved.includes(alias.toLowerCase())) {
    return { success: false, error: `'${alias}' is a reserved alias name` };
  }

  const data = loadAliases();
  const existing = data.aliases[alias];
  const isNew = !existing;

  data.aliases[alias] = {
    sessionPath,
    createdAt: existing ? existing.createdAt : new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    title: title || null
  };

  if (saveAliases(data)) {
    return {
      success: true,
      isNew,
      alias,
      sessionPath,
      title: data.aliases[alias].title
    };
  }

  return { success: false, error: 'Failed to save alias' };
}

/**
 * List all aliases
 */
function listAliases(options = {}) {
  const { search = null, limit = null } = options;
  const data = loadAliases();

  let aliases = Object.entries(data.aliases).map(([name, info]) => ({
    name,
    sessionPath: info.sessionPath,
    createdAt: info.createdAt,
    updatedAt: info.updatedAt,
    title: info.title
  }));

  aliases.sort((a, b) => (new Date(b.updatedAt || b.createdAt || 0).getTime() || 0) - (new Date(a.updatedAt || a.createdAt || 0).getTime() || 0));

  if (search) {
    const searchLower = search.toLowerCase();
    aliases = aliases.filter(a =>
      a.name.toLowerCase().includes(searchLower) ||
      (a.title && a.title.toLowerCase().includes(searchLower))
    );
  }

  if (limit && limit > 0) {
    aliases = aliases.slice(0, limit);
  }

  return aliases;
}

/**
 * Delete an alias
 */
function deleteAlias(alias) {
  const data = loadAliases();

  if (!data.aliases[alias]) {
    return { success: false, error: `Alias '${alias}' not found` };
  }

  const deleted = data.aliases[alias];
  delete data.aliases[alias];

  if (saveAliases(data)) {
    return {
      success: true,
      alias,
      deletedSessionPath: deleted.sessionPath
    };
  }

  return { success: false, error: 'Failed to delete alias' };
}

/**
 * Rename an alias
 */
function renameAlias(oldAlias, newAlias) {
  const data = loadAliases();

  if (!data.aliases[oldAlias]) {
    return { success: false, error: `Alias '${oldAlias}' not found` };
  }

  if (!newAlias || newAlias.length === 0) {
    return { success: false, error: 'New alias name cannot be empty' };
  }

  if (newAlias.length > 128) {
    return { success: false, error: 'New alias name cannot exceed 128 characters' };
  }

  if (!/^[a-zA-Z0-9_-]+$/.test(newAlias)) {
    return { success: false, error: 'New alias name must contain only letters, numbers, dashes, and underscores' };
  }

  const reserved = ['list', 'help', 'remove', 'delete', 'create', 'set'];
  if (reserved.includes(newAlias.toLowerCase())) {
    return { success: false, error: `'${newAlias}' is a reserved alias name` };
  }

  if (data.aliases[newAlias]) {
    return { success: false, error: `Alias '${newAlias}' already exists` };
  }

  const aliasData = data.aliases[oldAlias];
  delete data.aliases[oldAlias];

  aliasData.updatedAt = new Date().toISOString();
  data.aliases[newAlias] = aliasData;

  if (saveAliases(data)) {
    return {
      success: true,
      oldAlias,
      newAlias,
      sessionPath: aliasData.sessionPath
    };
  }

  data.aliases[oldAlias] = aliasData;
  delete data.aliases[newAlias];
  saveAliases(data);
  return { success: false, error: 'Failed to save renamed alias — rolled back to original' };
}

/**
 * Get session path by alias (convenience function)
 */
function resolveSessionAlias(aliasOrId) {
  const resolved = resolveAlias(aliasOrId);
  if (resolved) {
    return resolved.sessionPath;
  }
  return aliasOrId;
}

/**
 * Update alias title
 */
function updateAliasTitle(alias, title) {
  if (title !== null && typeof title !== 'string') {
    return { success: false, error: 'Title must be a string or null' };
  }

  const data = loadAliases();

  if (!data.aliases[alias]) {
    return { success: false, error: `Alias '${alias}' not found` };
  }

  data.aliases[alias].title = title || null;
  data.aliases[alias].updatedAt = new Date().toISOString();

  if (saveAliases(data)) {
    return {
      success: true,
      alias,
      title
    };
  }

  return { success: false, error: 'Failed to update alias title' };
}

/**
 * Get all aliases for a specific session
 */
function getAliasesForSession(sessionPath) {
  const data = loadAliases();
  const aliases = [];

  for (const [name, info] of Object.entries(data.aliases)) {
    if (info.sessionPath === sessionPath) {
      aliases.push({
        name,
        createdAt: info.createdAt,
        title: info.title
      });
    }
  }

  return aliases;
}

/**
 * Clean up aliases for non-existent sessions
 */
function cleanupAliases(sessionExists) {
  if (typeof sessionExists !== 'function') {
    return { totalChecked: 0, removed: 0, removedAliases: [], error: 'sessionExists must be a function' };
  }

  const data = loadAliases();
  const removed = [];

  for (const [name, info] of Object.entries(data.aliases)) {
    if (!sessionExists(info.sessionPath)) {
      removed.push({ name, sessionPath: info.sessionPath });
      delete data.aliases[name];
    }
  }

  if (removed.length > 0 && !saveAliases(data)) {
    log('[Aliases] Failed to save after cleanup');
    return {
      success: false,
      totalChecked: Object.keys(data.aliases).length + removed.length,
      removed: removed.length,
      removedAliases: removed,
      error: 'Failed to save after cleanup'
    };
  }

  return {
    success: true,
    totalChecked: Object.keys(data.aliases).length + removed.length,
    removed: removed.length,
    removedAliases: removed
  };
}

module.exports = {
  getAliasesPath,
  loadAliases,
  saveAliases,
  resolveAlias,
  setAlias,
  listAliases,
  deleteAlias,
  renameAlias,
  resolveSessionAlias,
  updateAliasTitle,
  getAliasesForSession,
  cleanupAliases
};
