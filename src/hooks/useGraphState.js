import { useCallback, useState } from 'react';
import { useGraph } from '../context/GraphContext';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000';

export function useGraphState() {
  const graph = useGraph();
  const [error, setError] = useState(null);
  const [validationResult, setValidationResult] = useState(null);

  // Convert ReactFlow nodes/edges to API format
  const toApiFormat = useCallback(() => {
    const nodes = graph.nodes.map(node => ({
      id: node.id,
      type: node.data.moduleType,
      config: node.data.config,
    }));

    const edges = graph.edges.map(edge => ({
      source: edge.source,
      target: edge.target,
      flow_type: edge.data?.flowType || 'remainder',
      amount: edge.data?.amount || 0,
      frequency: edge.data?.frequency || 'monthly',
      priority: edge.data?.priority || 0,
      condition: edge.data?.condition || null,
    }));

    return { nodes, edges };
  }, [graph.nodes, graph.edges]);

  // Validate graph
  const validateGraph = useCallback(async () => {
    setError(null);
    try {
      const { nodes, edges } = toApiFormat();
      const response = await axios.post(`${API_BASE}/api/graph/validate`, {
        nodes,
        edges,
      });
      setValidationResult(response.data);
      return response.data;
    } catch (err) {
      setError(err.response?.data?.error || err.message);
      return { valid: false, errors: [err.message] };
    }
  }, [toApiFormat]);

  // Run simulation
  const runSimulation = useCallback(async () => {
    setError(null);
    graph.setIsSimulating(true);

    try {
      const { nodes, edges } = toApiFormat();
      const response = await axios.post(`${API_BASE}/api/simulate`, {
        nodes,
        edges,
        user_profile: graph.userProfile,
        config: graph.simulationConfig,
      });

      if (response.data.success) {
        graph.setSimulationResult(response.data);
        return response.data;
      } else {
        throw new Error(response.data.error || 'Simulation failed');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
      return null;
    } finally {
      graph.setIsSimulating(false);
    }
  }, [toApiFormat, graph]);

  // Calculate tax
  const calculateTax = useCallback(async (income, deductions, credits) => {
    setError(null);
    try {
      const response = await axios.post(`${API_BASE}/api/tax/calculate`, {
        income,
        deductions,
        credits,
        user_profile: graph.userProfile,
        withholding: 0,
        estimated_payments: 0,
      });
      return response.data;
    } catch (err) {
      setError(err.response?.data?.error || err.message);
      return null;
    }
  }, [graph.userProfile]);

  // Calculate tax impact of a change
  const calculateTaxImpact = useCallback(async (baseScenario, change) => {
    setError(null);
    try {
      const response = await axios.post(`${API_BASE}/api/tax/impact`, {
        base_scenario: {
          ...baseScenario,
          user_profile: graph.userProfile,
        },
        change,
      });
      return response.data;
    } catch (err) {
      setError(err.response?.data?.error || err.message);
      return null;
    }
  }, [graph.userProfile]);

  // Save graph as JSON file download
  const saveGraph = useCallback(() => {
    const graphData = {
      nodes: graph.nodes,
      edges: graph.edges,
      userProfile: graph.userProfile,
      simulationConfig: graph.simulationConfig,
      savedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(graphData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `doughflow-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    return true;
  }, [graph.nodes, graph.edges, graph.userProfile, graph.simulationConfig]);

  // Load graph from uploaded JSON file
  const loadGraphFromFile = useCallback((file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const graphData = JSON.parse(e.target.result);
          graph.loadGraph(graphData);
          resolve(true);
        } catch (err) {
          setError('Invalid JSON file');
          reject(new Error('Invalid JSON file'));
        }
      };
      reader.onerror = () => {
        setError('Failed to read file');
        reject(new Error('Failed to read file'));
      };
      reader.readAsText(file);
    });
  }, [graph]);

  // Generate unique node ID
  const generateNodeId = useCallback((type) => {
    const existingIds = graph.nodes.map(n => n.id);
    let counter = 1;
    let id = `${type}_${counter}`;
    while (existingIds.includes(id)) {
      counter++;
      id = `${type}_${counter}`;
    }
    return id;
  }, [graph.nodes]);

  // Create a new node
  const createNode = useCallback((type, position, config = {}) => {
    const id = generateNodeId(type);
    const newNode = {
      id,
      type: 'customNode',
      position,
      data: {
        moduleType: type,
        config: {
          name: id.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
          ...config,
        },
        label: config.name || type.replace('_', ' '),
      },
    };
    graph.addNode(newNode);
    return newNode;
  }, [generateNodeId, graph]);

  return {
    // State
    error,
    validationResult,

    // Actions
    validateGraph,
    runSimulation,
    calculateTax,
    calculateTaxImpact,
    saveGraph,
    loadGraphFromFile,
    createNode,
    generateNodeId,
    toApiFormat,
  };
}

export default useGraphState;
