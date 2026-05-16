import path from "node:path";
import { fileURLToPath } from "node:url";
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

import {
  buildFailureMessage,
  buildMissingRunnerMessage,
  buildMissingExtensionMessage,
  formatRunnerPayload,
  truncateContent
} from "./lib/formatters.js";
import { extractSearchIntentFromEvent, detectSites } from "./lib/intent.js";
import { createDebugLogger } from "./lib/logging.js";
import {
  DEFAULT_EXTENSION_ID,
  DEFAULT_EXTENSION_ID_ENV,
  DEFAULT_INSTALL_URL,
  DEFAULT_INSTALL_URL_ENV,
  DEFAULT_TIMEOUT_MS,
  PLUGIN_DESCRIPTION,
  PLUGIN_ID,
  PLUGIN_NAME
} from "./lib/defaults.js";
import {
  buildRunnerArgs,
  extractJsonPayload,
  resolveRunnerPath,
  resolveTimeoutMs,
  runNodeScript
} from "./lib/runner.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function getPluginConfig(rawPluginConfig) {
  return rawPluginConfig && typeof rawPluginConfig === "object" ? rawPluginConfig : {};
}

function readEnvValue(name) {
  try {
    return typeof process !== "undefined" && process.env && typeof process.env[name] === "string"
      ? process.env[name].trim()
      : "";
  } catch (_) {
    return "";
  }
}

function getPluginRuntimeOptions(pluginConfig) {
  const extensionId = typeof pluginConfig.extensionId === "string" && pluginConfig.extensionId.trim()
    ? pluginConfig.extensionId.trim()
    : readEnvValue(DEFAULT_EXTENSION_ID_ENV) || DEFAULT_EXTENSION_ID;
  const browserApp = typeof pluginConfig.browserApp === "string" && pluginConfig.browserApp.trim()
    ? pluginConfig.browserApp.trim()
    : "";
  const installUrl = typeof pluginConfig.installUrl === "string" && pluginConfig.installUrl.trim()
    ? pluginConfig.installUrl.trim()
    : readEnvValue(DEFAULT_INSTALL_URL_ENV) || DEFAULT_INSTALL_URL;
  const timeoutMs = resolveTimeoutMs(pluginConfig, DEFAULT_TIMEOUT_MS);

  return {
    extensionId,
    browserApp,
    installUrl,
    timeoutMs
  };
}

async function handleSearchRoute({
  api,
  pluginConfig,
  appendDebugLog,
  text,
  hookName,
  hookMeta = {}
}) {
  appendDebugLog(`${hookName}.enter`, {
    ...hookMeta,
    text: typeof text === "string" ? text : ""
  });

  const intent = extractSearchIntentFromEvent({
    body: text,
    content: text
  });
  if (!intent) {
    appendDebugLog(`${hookName}.no_match`, {
      ...hookMeta
    });
    return null;
  }

  const runnerPath = resolveRunnerPath(pluginConfig, __dirname);
  if (!runnerPath) {
    appendDebugLog(`${hookName}.missing_runner`, {
      ...hookMeta,
      query: intent.query
    });
    return {
      handled: true,
      text: buildMissingRunnerMessage(__dirname)
    };
  }

  const runtimeOptions = getPluginRuntimeOptions(pluginConfig);
  const sites = detectSites(intent.original);

  if (!runtimeOptions.extensionId) {
    appendDebugLog(`${hookName}.missing_extension_id`, {
      ...hookMeta,
      query: intent.query,
      installUrl: runtimeOptions.installUrl
    });
    return {
      handled: true,
      text: buildMissingExtensionMessage({
        ...pluginConfig,
        extensionId: runtimeOptions.extensionId,
        installUrl: runtimeOptions.installUrl
      })
    };
  }

  api.logger?.info?.(
    `ai-compare-hard-router: ${hookName} matched query="${intent.query}" sites=${sites.join(",") || "default"} runner=${runnerPath}`
  );
  appendDebugLog(`${hookName}.match`, {
    ...hookMeta,
    query: intent.query,
    original: intent.original,
    matchedFrom: intent.matchedFrom,
    matchType: intent.matchType || "search",
    noSummary: intent.noSummary === true,
    sites,
    runnerPath,
    extensionId: runtimeOptions.extensionId,
    browserApp: runtimeOptions.browserApp,
    installUrl: runtimeOptions.installUrl,
    timeoutMs: runtimeOptions.timeoutMs
  });

  const execResult = await runNodeScript(
    buildRunnerArgs({
      runnerPath,
      query: intent.query,
      sites,
      extensionId: runtimeOptions.extensionId,
      browserApp: runtimeOptions.browserApp
    }),
    runtimeOptions.timeoutMs,
    api.logger
  );

  appendDebugLog(`${hookName}.runner_complete`, {
    ...hookMeta,
    query: intent.query,
    ok: execResult.ok,
    timedOut: execResult.timedOut,
    code: execResult.code,
    signal: execResult.signal,
    stdoutPreview: truncateContent(execResult.stdout || "", 800),
    stderrPreview: truncateContent(execResult.stderr || "", 800)
  });

  if (execResult.timedOut) {
    return {
      handled: true,
      text: buildFailureMessage({
        query: intent.query,
        detail: "Timed out waiting for the AI Compare runner to finish.",
        stderr: execResult.stderr
      })
    };
  }

  const payload = extractJsonPayload(execResult.stdout);
  if (!payload) {
    appendDebugLog(`${hookName}.bad_json`, {
      ...hookMeta,
      query: intent.query
    });
    return {
      handled: true,
      text: buildFailureMessage({
        query: intent.query,
        detail: "Runner did not return valid JSON.",
        stderr: [execResult.stderr, execResult.stdout].filter(Boolean).join("\n")
      })
    };
  }

  appendDebugLog(`${hookName}.handled`, {
    ...hookMeta,
    query: intent.query,
    payloadOk: payload?.ok === true,
    resultCount: Array.isArray(payload?.result?.results) ? payload.result.results.length : 0
  });

  return {
    handled: true,
    text: formatRunnerPayload(payload, {
      query: intent.query,
      pluginConfig: {
        ...pluginConfig,
        extensionId: runtimeOptions.extensionId,
        installUrl: runtimeOptions.installUrl
      }
    })
  };
}

export default definePluginEntry({
  id: PLUGIN_ID,
  name: PLUGIN_NAME,
  description: PLUGIN_DESCRIPTION,
  register(api) {
    const pluginConfig = getPluginConfig(api?.pluginConfig);
    const appendDebugLog = createDebugLogger(pluginConfig);

    appendDebugLog("register", {
      pluginId: PLUGIN_ID,
      hasPluginConfig: !!api?.pluginConfig,
      registrationMode: api?.registrationMode,
      onType: typeof api?.on
    });

    appendDebugLog("register.before_dispatch_hook_setup", {
      pluginId: PLUGIN_ID
    });
    api.on("before_dispatch", async (event) => {
      return await handleSearchRoute({
        api,
        pluginConfig,
        appendDebugLog,
        text: typeof event?.body === "string" && event.body.trim()
          ? event.body
          : typeof event?.content === "string"
            ? event.content
            : "",
        hookName: "before_dispatch",
        hookMeta: {
          channel: event?.channel,
          sessionKey: event?.sessionKey,
          senderId: event?.senderId,
          isGroup: event?.isGroup === true
        }
      });
    });

    appendDebugLog("register.before_agent_reply_hook_setup", {
      pluginId: PLUGIN_ID
    });
    api.on("before_agent_reply", async (event, ctx) => {
      const routeResult = await handleSearchRoute({
        api,
        pluginConfig,
        appendDebugLog,
        text: typeof event?.cleanedBody === "string" ? event.cleanedBody : "",
        hookName: "before_agent_reply",
        hookMeta: {
          trigger: ctx?.trigger,
          sessionKey: ctx?.sessionKey,
          channelId: ctx?.channelId,
          messageProvider: ctx?.messageProvider
        }
      });

      if (!routeResult?.handled) {
        return;
      }

      return {
        handled: true,
        reply: {
          text: routeResult.text || "NO_REPLY"
        },
        reason: "ai-compare-hard-router"
      };
    });
  }
});
