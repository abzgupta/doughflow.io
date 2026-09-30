import React, { createContext, useContext, useReducer, useCallback } from 'react';
import sampleGraph from '../examples/sampleGraph.json';

// Blank canvas (used by "New Graph")
const emptyState = {
  nodes: [],
  edges: [],
  userProfile: {
    filing_status: 'married_jointly',
    state: 'CA',
    age: 35,
    annual_salary: 150000,
    dependents: 0,
  },
  simulationConfig: {
    start_year: new Date().getFullYear(),
    start_month: 1,
    duration_months: 120,
  },
  simulationResult: null,
  isSimulating: false,
  selectedNode: null,
  selectedEdge: null,
  isDirty: false,
};

// Start with the example graph so first-time visitors see a working simulation
const initialState = {
  ...emptyState,
  nodes: sampleGraph.nodes,
  edges: sampleGraph.edges,
  userProfile: sampleGraph.userProfile,
  simulationConfig: sampleGraph.simulationConfig,
};

// Action types
const ActionTypes = {
  ADD_NODE: 'ADD_NODE',
  UPDATE_NODE: 'UPDATE_NODE',
  REMOVE_NODE: 'REMOVE_NODE',
  ADD_EDGE: 'ADD_EDGE',
  UPDATE_EDGE: 'UPDATE_EDGE',
  REMOVE_EDGE: 'REMOVE_EDGE',
  SET_NODES: 'SET_NODES',
  SET_EDGES: 'SET_EDGES',
  SET_USER_PROFILE: 'SET_USER_PROFILE',
  SET_SIMULATION_CONFIG: 'SET_SIMULATION_CONFIG',
  SET_SIMULATION_RESULT: 'SET_SIMULATION_RESULT',
  SET_IS_SIMULATING: 'SET_IS_SIMULATING',
  SELECT_NODE: 'SELECT_NODE',
  SELECT_EDGE: 'SELECT_EDGE',
  LOAD_GRAPH: 'LOAD_GRAPH',
  CLEAR_GRAPH: 'CLEAR_GRAPH',
  SET_DIRTY: 'SET_DIRTY',
};

// Reducer
function graphReducer(state, action) {
  switch (action.type) {
    case ActionTypes.ADD_NODE:
      return {
        ...state,
        nodes: [...state.nodes, action.payload],
        isDirty: true,
      };

    case ActionTypes.UPDATE_NODE:
      return {
        ...state,
        nodes: state.nodes.map(node =>
          node.id === action.payload.id
            ? { ...node, ...action.payload.updates }
            : node
        ),
        isDirty: true,
      };

    case ActionTypes.REMOVE_NODE:
      return {
        ...state,
        nodes: state.nodes.filter(node => node.id !== action.payload),
        edges: state.edges.filter(
          edge => edge.source !== action.payload && edge.target !== action.payload
        ),
        isDirty: true,
      };

    case ActionTypes.ADD_EDGE:
      return {
        ...state,
        edges: [...state.edges, action.payload],
        isDirty: true,
      };

    case ActionTypes.UPDATE_EDGE:
      return {
        ...state,
        edges: state.edges.map(edge =>
          edge.id === action.payload.id
            ? { ...edge, ...action.payload.updates }
            : edge
        ),
        isDirty: true,
      };

    case ActionTypes.REMOVE_EDGE:
      return {
        ...state,
        edges: state.edges.filter(edge => edge.id !== action.payload),
        isDirty: true,
      };

    case ActionTypes.SET_NODES:
      return {
        ...state,
        nodes: action.payload,
      };

    case ActionTypes.SET_EDGES:
      return {
        ...state,
        edges: action.payload,
      };

    case ActionTypes.SET_USER_PROFILE:
      return {
        ...state,
        userProfile: { ...state.userProfile, ...action.payload },
        isDirty: true,
      };

    case ActionTypes.SET_SIMULATION_CONFIG:
      return {
        ...state,
        simulationConfig: { ...state.simulationConfig, ...action.payload },
        isDirty: true,
      };

    case ActionTypes.SET_SIMULATION_RESULT:
      return {
        ...state,
        simulationResult: action.payload,
      };

    case ActionTypes.SET_IS_SIMULATING:
      return {
        ...state,
        isSimulating: action.payload,
      };

    case ActionTypes.SELECT_NODE:
      return {
        ...state,
        selectedNode: action.payload,
        selectedEdge: null,
      };

    case ActionTypes.SELECT_EDGE:
      return {
        ...state,
        selectedEdge: action.payload,
        selectedNode: null,
      };

    case ActionTypes.LOAD_GRAPH:
      return {
        ...state,
        nodes: action.payload.nodes || [],
        edges: action.payload.edges || [],
        userProfile: action.payload.userProfile || state.userProfile,
        simulationConfig: action.payload.simulationConfig || state.simulationConfig,
        isDirty: false,
      };

    case ActionTypes.CLEAR_GRAPH:
      return {
        ...emptyState,
      };

    case ActionTypes.SET_DIRTY:
      return {
        ...state,
        isDirty: action.payload,
      };

    default:
      return state;
  }
}

// Context
const GraphContext = createContext(null);

// Provider component
export function GraphProvider({ children }) {
  const [state, dispatch] = useReducer(graphReducer, initialState);

  // Action creators
  const addNode = useCallback((node) => {
    dispatch({ type: ActionTypes.ADD_NODE, payload: node });
  }, []);

  const updateNode = useCallback((id, updates) => {
    dispatch({ type: ActionTypes.UPDATE_NODE, payload: { id, updates } });
  }, []);

  const removeNode = useCallback((id) => {
    dispatch({ type: ActionTypes.REMOVE_NODE, payload: id });
  }, []);

  const addEdge = useCallback((edge) => {
    dispatch({ type: ActionTypes.ADD_EDGE, payload: edge });
  }, []);

  const updateEdge = useCallback((id, updates) => {
    dispatch({ type: ActionTypes.UPDATE_EDGE, payload: { id, updates } });
  }, []);

  const removeEdge = useCallback((id) => {
    dispatch({ type: ActionTypes.REMOVE_EDGE, payload: id });
  }, []);

  const setNodes = useCallback((nodes) => {
    dispatch({ type: ActionTypes.SET_NODES, payload: nodes });
  }, []);

  const setEdges = useCallback((edges) => {
    dispatch({ type: ActionTypes.SET_EDGES, payload: edges });
  }, []);

  const setUserProfile = useCallback((profile) => {
    dispatch({ type: ActionTypes.SET_USER_PROFILE, payload: profile });
  }, []);

  const setSimulationConfig = useCallback((config) => {
    dispatch({ type: ActionTypes.SET_SIMULATION_CONFIG, payload: config });
  }, []);

  const setSimulationResult = useCallback((result) => {
    dispatch({ type: ActionTypes.SET_SIMULATION_RESULT, payload: result });
  }, []);

  const setIsSimulating = useCallback((isSimulating) => {
    dispatch({ type: ActionTypes.SET_IS_SIMULATING, payload: isSimulating });
  }, []);

  const selectNode = useCallback((nodeId) => {
    dispatch({ type: ActionTypes.SELECT_NODE, payload: nodeId });
  }, []);

  const selectEdge = useCallback((edgeId) => {
    dispatch({ type: ActionTypes.SELECT_EDGE, payload: edgeId });
  }, []);

  const loadGraph = useCallback((graphData) => {
    dispatch({ type: ActionTypes.LOAD_GRAPH, payload: graphData });
  }, []);

  const clearGraph = useCallback(() => {
    dispatch({ type: ActionTypes.CLEAR_GRAPH });
  }, []);

  const value = {
    ...state,
    addNode,
    updateNode,
    removeNode,
    addEdge,
    updateEdge,
    removeEdge,
    setNodes,
    setEdges,
    setUserProfile,
    setSimulationConfig,
    setSimulationResult,
    setIsSimulating,
    selectNode,
    selectEdge,
    loadGraph,
    clearGraph,
  };

  return (
    <GraphContext.Provider value={value}>
      {children}
    </GraphContext.Provider>
  );
}

// Hook
export function useGraph() {
  const context = useContext(GraphContext);
  if (!context) {
    throw new Error('useGraph must be used within a GraphProvider');
  }
  return context;
}

export default GraphContext;
