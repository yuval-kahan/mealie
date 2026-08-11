export type NotebookNodeType = "section_group" | "section" | "page";

export interface NotebookHighlightCategory {
  id: string;
  name: string;
  color: string;
}

export interface NotebookBase {
  title: string;
  description?: string | null;
  color: string;
  icon: string;
  isFavorite: boolean;
  isPinned: boolean;
  position: number;
  settings: Record<string, unknown>;
}

export interface NotebookSummary extends NotebookBase {
  id: string;
  groupId: string;
  householdId: string;
  userId: string;
  nodeCount: number;
  pageCount: number;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface NotebookNode {
  id: string;
  notebookId: string;
  parentId?: string | null;
  groupId: string;
  householdId: string;
  userId: string;
  nodeType: NotebookNodeType;
  title: string;
  contentHtml: string;
  position: number;
  isCollapsed: boolean;
  isFavorite: boolean;
  isPinned: boolean;
  color?: string | null;
  tags: string[];
  categories: string[];
  highlightCategories: NotebookHighlightCategory[];
  settings: Record<string, unknown>;
  contentVersion: number;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface NotebookDetail extends NotebookSummary {
  nodes: NotebookNode[];
}

export interface NotebookCreate extends NotebookBase {
  createStarterPage: boolean;
}

export interface NotebookNodeCreate {
  parentId?: string | null;
  nodeType: NotebookNodeType;
  title: string;
  contentHtml: string;
  position: number;
  isCollapsed: boolean;
  isFavorite: boolean;
  isPinned: boolean;
  color?: string | null;
  tags: string[];
  categories: string[];
  highlightCategories: NotebookHighlightCategory[];
  settings: Record<string, unknown>;
}

export interface NotebookRevision {
  id: string;
  nodeId: string;
  userId: string;
  title: string;
  contentHtml: string;
  settings: Record<string, unknown>;
  contentVersion: number;
  createdAt?: string | null;
}

export interface NotebookSearchResult {
  notebookId: string;
  notebookTitle: string;
  nodeId: string;
  nodeTitle: string;
  nodeType: NotebookNodeType;
  excerpt: string;
  updatedAt?: string | null;
}

export interface NotebookTOCRequest {
  language: string;
  pagesPerChunk: number;
}

export interface NotebookTOCResponse {
  tocNode: NotebookNode;
  chunkCount: number;
  providerCount: number;
}
