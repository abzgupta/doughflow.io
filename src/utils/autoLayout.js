// Layered left-to-right layout: a node's column is its depth (the longest
// path from a node with no incoming edges), and nodes in the same column are
// stacked vertically.

const DEFAULT_WIDTH = 200;
const DEFAULT_HEIGHT = 100;
const COLUMN_GAP = 120;
const ROW_GAP = 40;
const SWEEPS = 4;

// Edges that close a loop, found by depth-first search. Ignoring them turns
// the graph into a DAG so depths are well defined.
function findBackEdges(ids, outgoing) {
  const state = {}; // undefined = unvisited, 1 = on stack, 2 = done
  const back = new Set();

  const visit = (id) => {
    state[id] = 1;
    for (const target of outgoing[id]) {
      if (state[target] === 1) {
        back.add(`${id}->${target}`);
      } else if (!state[target]) {
        visit(target);
      }
    }
    state[id] = 2;
  };

  ids.forEach((id) => { if (!state[id]) visit(id); });
  return back;
}

function computeDepths(ids, links) {
  const depth = Object.fromEntries(ids.map((id) => [id, 0]));
  const indegree = Object.fromEntries(ids.map((id) => [id, 0]));
  const outgoing = Object.fromEntries(ids.map((id) => [id, []]));
  links.forEach(([s, t]) => { outgoing[s].push(t); indegree[t] += 1; });

  // Kahn's algorithm: a node's depth is one more than its deepest parent
  const queue = ids.filter((id) => indegree[id] === 0);
  while (queue.length) {
    const id = queue.shift();
    for (const target of outgoing[id]) {
      depth[target] = Math.max(depth[target], depth[id] + 1);
      indegree[target] -= 1;
      if (indegree[target] === 0) queue.push(target);
    }
  }
  return depth;
}

// Reorder each column by the average position of its neighbors in the
// adjacent column (barycenter heuristic), which reduces crossing edges
function reduceCrossings(columns, parents, children) {
  const index = {};
  const reindex = (column) => column.forEach((id, i) => { index[id] = i; });
  columns.forEach(reindex);

  const sortBy = (column, neighbors) => {
    const key = (id) => {
      const placed = neighbors[id].filter((n) => n in index);
      if (!placed.length) return index[id];
      return placed.reduce((sum, n) => sum + index[n], 0) / placed.length;
    };
    const keys = Object.fromEntries(column.map((id) => [id, key(id)]));
    column.sort((a, b) => keys[a] - keys[b]);
    reindex(column);
  };

  for (let sweep = 0; sweep < SWEEPS; sweep++) {
    for (let c = 1; c < columns.length; c++) sortBy(columns[c], parents);
    for (let c = columns.length - 2; c >= 0; c--) sortBy(columns[c], children);
  }
}

/**
 * Return a copy of `nodes` with positions laid out in columns by depth.
 * Uses React Flow's measured node sizes when available.
 */
export function autoLayout(nodes, edges) {
  if (!nodes.length) return nodes;

  const ids = nodes.map((n) => n.id);
  const known = new Set(ids);
  const allLinks = edges
    .filter((e) => known.has(e.source) && known.has(e.target) && e.source !== e.target)
    .map((e) => [e.source, e.target]);

  const outgoing = Object.fromEntries(ids.map((id) => [id, []]));
  allLinks.forEach(([s, t]) => outgoing[s].push(t));
  // Visit sources first so loops are broken at their far end
  const order = [...ids].sort((a, b) =>
    allLinks.some(([, t]) => t === a) - allLinks.some(([, t]) => t === b));
  const back = findBackEdges(order, outgoing);
  const links = allLinks.filter(([s, t]) => !back.has(`${s}->${t}`));

  const depth = computeDepths(ids, links);

  const parents = Object.fromEntries(ids.map((id) => [id, []]));
  const children = Object.fromEntries(ids.map((id) => [id, []]));
  links.forEach(([s, t]) => { parents[t].push(s); children[s].push(t); });

  // Start each column in the user's current top-to-bottom order
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
  const columns = [];
  [...ids]
    .sort((a, b) => (byId[a].position?.y ?? 0) - (byId[b].position?.y ?? 0))
    .forEach((id) => { (columns[depth[id]] ||= []).push(id); });
  for (let c = 0; c < columns.length; c++) columns[c] ||= [];

  reduceCrossings(columns, parents, children);

  const width = (n) => n.width || DEFAULT_WIDTH;
  const height = (n) => n.height || DEFAULT_HEIGHT;
  const columnWidth = Math.max(...nodes.map(width)) + COLUMN_GAP;

  const position = {};
  columns.forEach((column, c) => {
    const total = column.reduce((sum, id) => sum + height(byId[id]), 0)
      + ROW_GAP * Math.max(column.length - 1, 0);
    let y = -total / 2;
    column.forEach((id) => {
      position[id] = { x: c * columnWidth, y };
      y += height(byId[id]) + ROW_GAP;
    });
  });

  return nodes.map((n) => ({ ...n, position: position[n.id] }));
}
