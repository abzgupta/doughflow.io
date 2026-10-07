import React, { useCallback, useRef, useState } from 'react';
import ReactFlow, {
  addEdge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Button, Tooltip, message } from 'antd';
import { ApartmentOutlined } from '@ant-design/icons';

import { nodeTypes } from '../nodes';
import FlowToolbar from './FlowToolbar';
import EdgeConfigModal from '../forms/EdgeConfigModal';
import NodeConfigDrawer from '../forms/NodeConfigDrawer';
import { useGraph } from '../../context/GraphContext';
import { useGraphState } from '../../hooks/useGraphState';
import { autoLayout } from '../../utils/autoLayout';

// Edge styles based on flow type
const getEdgeStyle = (flowType, isInactive = false) => {
  if (isInactive) {
    return { stroke: '#d9d9d9', strokeWidth: 1, opacity: 0.5 };
  }
  switch (flowType) {
    case 'fixed':
      return { stroke: '#1890ff', strokeWidth: 2 };
    case 'percentage':
      return { stroke: '#52c41a', strokeWidth: 2, strokeDasharray: '5,5' };
    case 'remainder':
      return { stroke: '#722ed1', strokeWidth: 2 };
    default:
      return { stroke: '#bfbfbf', strokeWidth: 1 };
  }
};

// Edge label for amount
const getEdgeLabel = (data) => {
  if (!data) return '';
  if (data.flowType === 'fixed') {
    return `$${data.amount?.toLocaleString() || 0}/mo`;
  } else if (data.flowType === 'percentage') {
    return `${data.amount || 0}%`;
  } else {
    return 'Remainder';
  }
};

function FlowCanvas() {
  const reactFlowWrapper = useRef(null);
  const graph = useGraph();
  const { createNode } = useGraphState();

  // ReactFlow state
  const [nodes, setNodes, onNodesChange] = useNodesState(graph.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(graph.edges);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);

  // Track if we're syncing to prevent loops
  const isSyncingRef = useRef(false);

  // Modal states
  const [edgeModalOpen, setEdgeModalOpen] = useState(false);
  const [pendingEdge, setPendingEdge] = useState(null);
  const [nodeDrawerOpen, setNodeDrawerOpen] = useState(false);
  const [selectedNodeForEdit, setSelectedNodeForEdit] = useState(null);

  // Sync FROM context TO local state (when graph is loaded externally or simulation updates)
  React.useEffect(() => {
    if (isSyncingRef.current) return;

    // Check if this is an external change (different node IDs)
    const localIds = nodes.map(n => n.id).sort().join(',');
    const contextIds = graph.nodes.map(n => n.id).sort().join(',');

    if (localIds !== contextIds) {
      setNodes(graph.nodes);
      return;
    }

    // Also check for simulation-related data changes (isInactive, simulatedBalance)
    let hasSimulationChanges = false;
    for (const contextNode of graph.nodes) {
      const localNode = nodes.find(n => n.id === contextNode.id);
      if (localNode) {
        if (localNode.data?.isInactive !== contextNode.data?.isInactive ||
            localNode.data?.simulatedBalance !== contextNode.data?.simulatedBalance) {
          hasSimulationChanges = true;
          break;
        }
      }
    }

    if (hasSimulationChanges) {
      setNodes(graph.nodes);
    }
  }, [graph.nodes, nodes, setNodes]);

  React.useEffect(() => {
    const localIds = edges.map(e => e.id).sort().join(',');
    const contextIds = graph.edges.map(e => e.id).sort().join(',');

    if (localIds !== contextIds && !isSyncingRef.current) {
      setEdges(graph.edges);
    }
  }, [graph.edges]);

  // Sync FROM local state TO context when nodes/edges change
  React.useEffect(() => {
    isSyncingRef.current = true;
    graph.setNodes(nodes);
    isSyncingRef.current = false;
  }, [nodes]);

  React.useEffect(() => {
    isSyncingRef.current = true;
    graph.setEdges(edges);
    isSyncingRef.current = false;
  }, [edges]);

  // Update edge styles when nodes become inactive
  React.useEffect(() => {
    // Build a set of inactive node IDs
    const inactiveNodeIds = new Set(
      nodes.filter(n => n.data?.isInactive).map(n => n.id)
    );

    // Check if any edges need style updates
    let needsUpdate = false;
    const updatedEdges = edges.map(edge => {
      const isEdgeInactive = inactiveNodeIds.has(edge.source) || inactiveNodeIds.has(edge.target);
      const currentlyInactive = edge.data?.isInactive;

      if (isEdgeInactive !== currentlyInactive) {
        needsUpdate = true;
        const style = getEdgeStyle(edge.data?.flowType, isEdgeInactive);
        return {
          ...edge,
          style,
          animated: isEdgeInactive ? false : edge.data?.flowType === 'remainder',
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: style.stroke,
          },
          data: {
            ...edge.data,
            isInactive: isEdgeInactive,
          },
        };
      }
      return edge;
    });

    if (needsUpdate) {
      setEdges(updatedEdges);
    }
  }, [nodes, edges, setEdges]);

  // Handle new edge connection
  const onConnect = useCallback((params) => {
    // Open modal to configure the edge
    setPendingEdge(params);
    setEdgeModalOpen(true);
  }, []);

  // Handle edge configuration save
  const handleEdgeSave = useCallback((edgeConfig) => {
    if (!pendingEdge) return;

    const newEdge = {
      ...pendingEdge,
      id: `e-${pendingEdge.source}-${pendingEdge.target}`,
      type: 'default',
      animated: edgeConfig.flowType === 'remainder',
      style: getEdgeStyle(edgeConfig.flowType),
      label: getEdgeLabel(edgeConfig),
      labelStyle: { fontSize: 11, fontWeight: 500 },
      labelBgStyle: { fill: 'white', fillOpacity: 0.8 },
      labelBgPadding: [4, 2],
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: getEdgeStyle(edgeConfig.flowType).stroke,
      },
      data: edgeConfig,
    };

    setEdges((eds) => addEdge(newEdge, eds));
    setPendingEdge(null);
    setEdgeModalOpen(false);
    message.success('Flow connection created');
  }, [pendingEdge, setEdges]);

  // Handle node click
  const onNodeClick = useCallback((event, node) => {
    setSelectedNodeForEdit(node);
    setNodeDrawerOpen(true);
    graph.selectNode(node.id);
  }, [graph]);

  // Handle edge click
  const onEdgeClick = useCallback((event, edge) => {
    setPendingEdge(edge);
    setEdgeModalOpen(true);
    graph.selectEdge(edge.id);
  }, [graph]);

  // Handle node drag over (for toolbar drag-and-drop)
  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Handle node drop from toolbar
  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow');
      if (!type || !reactFlowInstance) return;

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNode = createNode(type, position);
      setNodes((nds) => [...nds, newNode]);
      message.success(`Added ${type.replace('_', ' ')}`);
    },
    [reactFlowInstance, createNode, setNodes]
  );

  // Handle add node from toolbar click
  const handleAddNodeFromToolbar = useCallback(
    (type) => {
      // Add at center of viewport
      if (!reactFlowInstance) return;

      const { x, y, zoom } = reactFlowInstance.getViewport();
      const centerX = (window.innerWidth / 2 - x) / zoom;
      const centerY = (window.innerHeight / 2 - y) / zoom;

      const newNode = createNode(type, { x: centerX, y: centerY });
      setNodes((nds) => [...nds, newNode]);
      message.success(`Added ${type.replace('_', ' ')}`);
    },
    [reactFlowInstance, createNode, setNodes]
  );

  // Handle node config update
  const handleNodeUpdate = useCallback(
    (nodeId, config) => {
      setNodes((nds) =>
        nds.map((node) =>
          node.id === nodeId
            ? {
                ...node,
                data: {
                  ...node.data,
                  config,
                  label: config.name || node.data.label,
                },
              }
            : node
        )
      );
      message.success('Node updated');
    },
    [setNodes]
  );

  // Handle node delete
  const handleNodeDelete = useCallback(
    (nodeId) => {
      setNodes((nds) => nds.filter((node) => node.id !== nodeId));
      setEdges((eds) =>
        eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId)
      );
      setNodeDrawerOpen(false);
      message.success('Node deleted');
    },
    [setNodes, setEdges]
  );

  // Handle edge update
  const handleEdgeUpdate = useCallback(
    (edgeId, edgeConfig) => {
      setEdges((eds) =>
        eds.map((edge) =>
          edge.id === edgeId
            ? {
                ...edge,
                animated: edgeConfig.flowType === 'remainder',
                style: getEdgeStyle(edgeConfig.flowType),
                label: getEdgeLabel(edgeConfig),
                markerEnd: {
                  type: MarkerType.ArrowClosed,
                  color: getEdgeStyle(edgeConfig.flowType).stroke,
                },
                data: edgeConfig,
              }
            : edge
        )
      );
      setPendingEdge(null);
      setEdgeModalOpen(false);
      message.success('Flow updated');
    },
    [setEdges]
  );

  // Handle edge delete
  const handleEdgeDelete = useCallback(
    (edgeId) => {
      setEdges((eds) => eds.filter((edge) => edge.id !== edgeId));
      setPendingEdge(null);
      setEdgeModalOpen(false);
      message.success('Flow deleted');
    },
    [setEdges]
  );

  // Line nodes up in columns by depth: sources on the left, each child one
  // column to the right of its deepest parent
  const handleAutoArrange = useCallback(() => {
    setNodes((nds) => autoLayout(nds, edges));
    // Let React Flow apply the new positions before re-fitting the view
    requestAnimationFrame(() => reactFlowInstance?.fitView({ padding: 0.15, duration: 300 }));
  }, [edges, setNodes, reactFlowInstance]);

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      <FlowToolbar onAddNode={handleAddNodeFromToolbar} />

      <div ref={reactFlowWrapper} style={{ flex: 1, height: '100%' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          onInit={setReactFlowInstance}
          onDrop={onDrop}
          onDragOver={onDragOver}
          nodeTypes={nodeTypes}
          fitView
          snapToGrid
          snapGrid={[15, 15]}
          defaultEdgeOptions={{
            type: 'default',
          }}
        >
          <Background variant="dots" gap={15} size={1} />
          <Controls />
          <Panel position="top-right">
            <Tooltip title="Line nodes up in columns: each node one column right of its deepest parent">
              <Button icon={<ApartmentOutlined rotate={-90} />} onClick={handleAutoArrange}>
                Auto-arrange
              </Button>
            </Tooltip>
          </Panel>
          <MiniMap
            nodeColor={(node) => {
              // Show inactive nodes in gray
              if (node.data?.isInactive) {
                return '#d9d9d9';
              }
              const typeColors = {
                salary: '#52c41a',
                savings_account: '#1890ff',
                stock_portfolio: '#722ed1',
                four_oh_one_k: '#eb2f96',
                ira: '#fa8c16',
                five_twenty_nine: '#13c2c2',
                real_estate: '#a0522d',
                mortgage: '#f5222d',
                debt: '#cf1322',
                expense: '#fa541c',
              };
              return typeColors[node.data?.moduleType] || '#bfbfbf';
            }}
            maskColor="rgba(240, 240, 240, 0.6)"
          />
        </ReactFlow>
      </div>

      {/* Edge Configuration Modal */}
      <EdgeConfigModal
        open={edgeModalOpen}
        edge={pendingEdge}
        onSave={pendingEdge?.id ? handleEdgeUpdate : handleEdgeSave}
        onDelete={pendingEdge?.id ? () => handleEdgeDelete(pendingEdge.id) : null}
        onCancel={() => {
          setPendingEdge(null);
          setEdgeModalOpen(false);
        }}
      />

      {/* Node Configuration Drawer */}
      <NodeConfigDrawer
        open={nodeDrawerOpen}
        node={selectedNodeForEdit}
        onUpdate={handleNodeUpdate}
        onDelete={handleNodeDelete}
        onClose={() => {
          setSelectedNodeForEdit(null);
          setNodeDrawerOpen(false);
        }}
      />
    </div>
  );
}

export default FlowCanvas;
