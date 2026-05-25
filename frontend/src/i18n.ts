export type Locale = "zh" | "en";

export type FormState = {
  title: string;
  doi: string;
  authors: string;
  year: string;
  journal: string;
  abstract: string;
  query: string;
};

export type Translation = {
  app: {
    subtitle: string;
    eyebrow: string;
    headline: string;
    health: string;
    language: string;
  };
  nav: {
    register: string;
    upload: string;
    extract: string;
    query: string;
    verify: string;
  };
  runtime: {
    title: string;
    apiKey: string;
    apiKeyPlaceholder: string;
    save: string;
    configured: string;
    missing: string;
    ready: string;
    pending: string;
    paper: string;
    document: string;
    evidence: string;
  };
  status: {
    ready: string;
    apiKeySaved: string;
    apiKeyCleared: string;
    registered: (paperId: string) => string;
    parsed: (count: number) => string;
    extractionPersisted: string;
    answerAbstained: string;
    evidenceAnswerReady: string;
  };
  errors: {
    unauthorized: string;
    registrationFailed: string;
    uploadFailed: string;
    extractionFailed: string;
    queryFailed: string;
  };
  register: {
    title: string;
    titleLabel: string;
    doi: string;
    year: string;
    authors: string;
    journal: string;
    abstract: string;
    button: string;
  };
  upload: {
    title: string;
    placeholder: string;
    helper: string;
    button: string;
    chunks: string;
    evidence: string;
    parsed: string;
  };
  extract: {
    title: string;
    subtitle: string;
    button: string;
  };
  query: {
    title: string;
    button: string;
    empty: string;
    results: string;
    spans: string;
    answered: string;
    abstained: string;
  };
};

export const localeStorageKey = "ebrag.locale";

export function detectInitialLocale(): Locale {
  try {
    const saved = localStorage.getItem(localeStorageKey);
    if (saved === "zh" || saved === "en") {
      return saved;
    }
  } catch {
    return "zh";
  }

  const browserLanguage = navigator.language.toLowerCase();
  return browserLanguage.startsWith("en") ? "en" : "zh";
}

export function defaultForm(locale: Locale): FormState {
  const stamp = Date.now();
  if (locale === "en") {
    return {
      title: "Compound X reduces IL-6 in APP/PS1 mice",
      doi: `10.0000/local-${stamp}`,
      authors: "Li, Wang",
      year: "2026",
      journal: "Local Evidence Review",
      abstract: "Compound X reduced IL-6 in a mouse model.",
      query: "Does Compound X reduce IL-6 in animal studies?"
    };
  }

  return {
    title: "化合物 X 可降低 APP/PS1 小鼠的 IL-6",
    doi: `10.0000/local-${stamp}`,
    authors: "Li, Wang",
    year: "2026",
    journal: "本地证据综述",
    abstract: "化合物 X 在小鼠模型中降低了 IL-6。",
    query: "化合物 X 是否会降低动物研究中的 IL-6？"
  };
}

const valueLabels: Record<Locale, Record<string, string>> = {
  zh: {
    answered: "已回答",
    abstained: "已拒答",
    configured: "已配置",
    missing: "缺失",
    pending: "待完成",
    ready: "就绪",
    parsed: "已解析",
    sufficient: "证据充分",
    partial: "部分充分",
    insufficient: "证据不足",
    supported: "支持",
    partially_supported: "部分支持",
    unsupported: "不支持",
    contradicted: "冲突",
    wrong_scope: "范围不符",
    overgeneralized: "过度泛化",
    uncited_numeric: "数值未引用",
    unverified: "未验证"
  },
  en: {
    answered: "answered",
    abstained: "abstained",
    configured: "configured",
    missing: "missing",
    pending: "pending",
    ready: "ready",
    parsed: "parsed",
    sufficient: "sufficient",
    partial: "partial",
    insufficient: "insufficient",
    supported: "supported",
    partially_supported: "partially supported",
    unsupported: "unsupported",
    contradicted: "contradicted",
    wrong_scope: "wrong scope",
    overgeneralized: "overgeneralized",
    uncited_numeric: "uncited numeric",
    unverified: "unverified"
  }
};

export function localizeValue(locale: Locale, value: string | null | undefined): string {
  if (!value) {
    return "";
  }
  return valueLabels[locale][value] ?? value;
}

export const copy: Record<Locale, Translation> = {
  zh: {
    app: {
      subtitle: "单机文献证据引擎",
      eyebrow: "循证系统综述工作台",
      headline: "在一个工作台完成文献导入、结构化抽取和带引用问答。",
      health: "健康检查",
      language: "语言"
    },
    nav: {
      register: "登记文献",
      upload: "上传原文",
      extract: "抽取证据",
      query: "证据问答",
      verify: "核验"
    },
    runtime: {
      title: "运行状态",
      apiKey: "API Key",
      apiKeyPlaceholder: "X-API-Key",
      save: "保存",
      configured: "已配置",
      missing: "缺失",
      ready: "就绪",
      pending: "待完成",
      paper: "文献",
      document: "文档",
      evidence: "证据"
    },
    status: {
      ready: "就绪",
      apiKeySaved: "API Key 已保存",
      apiKeyCleared: "API Key 已清除",
      registered: (paperId) => `已登记 ${paperId}`,
      parsed: (count) => `已解析 ${count} 个切块`,
      extractionPersisted: "抽取结果已保存",
      answerAbstained: "证据不足，系统已拒答",
      evidenceAnswerReady: "证据答案已生成"
    },
    errors: {
      unauthorized: "API Key 缺失或错误。请在左侧运行状态中保存部署 API Key。",
      registrationFailed: "文献登记失败",
      uploadFailed: "上传失败",
      extractionFailed: "抽取失败",
      queryFailed: "查询失败"
    },
    register: {
      title: "登记文献",
      titleLabel: "标题",
      doi: "DOI",
      year: "年份",
      authors: "作者",
      journal: "期刊",
      abstract: "摘要",
      button: "登记文献"
    },
    upload: {
      title: "上传原文",
      placeholder: "PDF、XML 或 TXT 原文",
      helper: "自动保存到 MinIO，并解析切块与证据片段",
      button: "上传并解析",
      chunks: "切块",
      evidence: "证据",
      parsed: "解析记录"
    },
    extract: {
      title: "结构化抽取",
      subtitle: "结构化结果",
      button: "保存示例抽取"
    },
    query: {
      title: "证据问答",
      button: "查询",
      empty: "带引用的答案句子、声明和核验结论会显示在这里。",
      results: "结果",
      spans: "证据片段",
      answered: "已回答",
      abstained: "已拒答"
    }
  },
  en: {
    app: {
      subtitle: "Single-node review engine",
      eyebrow: "Evidence-grounded systematic review",
      headline: "Literature intake, extraction, and cited answers in one workspace.",
      health: "Health",
      language: "Language"
    },
    nav: {
      register: "Register",
      upload: "Upload",
      extract: "Extract",
      query: "Query",
      verify: "Verify"
    },
    runtime: {
      title: "Runtime",
      apiKey: "API key",
      apiKeyPlaceholder: "X-API-Key",
      save: "Save",
      configured: "configured",
      missing: "missing",
      ready: "ready",
      pending: "pending",
      paper: "Paper",
      document: "Document",
      evidence: "Evidence"
    },
    status: {
      ready: "Ready",
      apiKeySaved: "API key saved",
      apiKeyCleared: "API key cleared",
      registered: (paperId) => `Registered ${paperId}`,
      parsed: (count) => `Parsed ${count} chunks`,
      extractionPersisted: "Extraction persisted",
      answerAbstained: "Answer abstained",
      evidenceAnswerReady: "Evidence answer ready"
    },
    errors: {
      unauthorized: "API key missing or invalid. Save the deployment API key in Runtime.",
      registrationFailed: "Registration failed",
      uploadFailed: "Upload failed",
      extractionFailed: "Extraction failed",
      queryFailed: "Query failed"
    },
    register: {
      title: "Register literature",
      titleLabel: "Title",
      doi: "DOI",
      year: "Year",
      authors: "Authors",
      journal: "Journal",
      abstract: "Abstract",
      button: "Register paper"
    },
    upload: {
      title: "Upload source document",
      placeholder: "PDF, XML, or TXT source",
      helper: "MinIO object, parsed chunks, evidence spans",
      button: "Upload and parse",
      chunks: "Chunks",
      evidence: "Evidence",
      parsed: "Parsed"
    },
    extract: {
      title: "Extraction",
      subtitle: "Structured results",
      button: "Persist sample extraction"
    },
    query: {
      title: "Evidence answer",
      button: "Query",
      empty: "Cited answer sentences, claims, and verification verdicts appear here.",
      results: "Results",
      spans: "Spans",
      answered: "answered",
      abstained: "abstained"
    }
  }
};
