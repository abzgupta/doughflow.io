import BaseNode from './BaseNode';

// Export all node types
// We use a single flexible BaseNode component that adapts to the module type
export const nodeTypes = {
  customNode: BaseNode,
};

export { BaseNode };
