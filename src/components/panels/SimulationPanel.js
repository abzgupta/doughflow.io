import React, { useState, useCallback, useMemo, useRef } from 'react';
import {
  Card,
  Button,
  Space,
  Typography,
  Slider,
  Statistic,
  Row,
  Col,
  Table,
  Tabs,
  Progress,
  Tag,
  Spin,
  Alert,
  Tooltip,
  Divider,
  message,
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StepForwardOutlined,
  FastForwardOutlined,
  LineChartOutlined,
  DollarOutlined,
  SwapOutlined,
  ReloadOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import { useGraph } from '../../context/GraphContext';
import { useGraphState } from '../../hooks/useGraphState';
import TransactionModal from './TransactionModal';
import axios from 'axios';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Format currency
const formatCurrency = (value) => {
  if (value === undefined || value === null) return '-';
  const isNegative = value < 0;
  const formatted = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Math.abs(value));
  return isNegative ? `(${formatted})` : formatted;
};

// Format date from month number
const formatDate = (monthNumber, startYear, startMonth) => {
  const totalMonths = startMonth - 1 + monthNumber;
  const year = startYear + Math.floor(totalMonths / 12);
  const month = (totalMonths % 12) + 1;
  return `${month}/${year}`;
};

// Get year and month from month number
const getYearMonth = (monthNumber, startYear, startMonth) => {
  const totalMonths = startMonth - 1 + monthNumber;
  const year = startYear + Math.floor(totalMonths / 12);
  const month = (totalMonths % 12) + 1;
  return { year, month };
};

function SimulationPanel() {
  const graph = useGraph();
  const { runSimulation, validateGraph, error, toApiFormat } = useGraphState();
  const [currentMonth, setCurrentMonth] = useState(1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playInterval, setPlayInterval] = useState(null);

  // Interactive mode state
  const [transactionModalOpen, setTransactionModalOpen] = useState(false);
  const [isTransacting, setIsTransacting] = useState(false);
  const [nodeStates, setNodeStates] = useState({});
  const [hasModifications, setHasModifications] = useState(false);

  const result = graph.simulationResult;
  const config = graph.simulationConfig;

  // Track last processed state to avoid infinite loops
  const lastProcessedRef = useRef({ month: null, resultId: null });

  // Update node inactive status when current month changes
  React.useEffect(() => {
    if (!result || !result.snapshots || currentMonth < 1) return;

    const snapshot = result.snapshots[currentMonth - 1];
    if (!snapshot) return;

    // Create a stable identifier for this result (use length as proxy)
    const resultId = result.snapshots.length;

    // Skip if we've already processed this exact state
    if (lastProcessedRef.current.month === currentMonth &&
        lastProcessedRef.current.resultId === resultId) {
      return;
    }

    const inactiveNodesFromSnapshot = snapshot.inactive_nodes || [];

    // Update nodes - read graph.nodes directly (not in deps to avoid loop)
    const updatedNodes = graph.nodes.map(node => {
      const moduleType = node.data?.moduleType;
      const isDebtType = moduleType === 'debt' || moduleType === 'mortgage';

      // Use modified balance if we have modifications, otherwise use snapshot
      let newBalance = snapshot.node_balances[node.id];
      if (hasModifications && nodeStates[node.id]?.balance !== undefined) {
        newBalance = nodeStates[node.id].balance;
      }

      // Determine if node is inactive:
      // 1. From snapshot's inactive_nodes list, OR
      // 2. It's a debt that was paid off (balance ~= 0) after modifications
      const isInactiveFromSnapshot = inactiveNodesFromSnapshot.includes(node.id);
      const isPaidOffDebt = isDebtType && Math.abs(newBalance) < 0.01;
      const isInactive = isInactiveFromSnapshot || isPaidOffDebt;

      if (node.data.isInactive !== isInactive || node.data.simulatedBalance !== newBalance) {
        return {
          ...node,
          data: {
            ...node.data,
            isInactive,
            simulatedBalance: newBalance,
          },
        };
      }
      return node;
    });

    // Only update if there were actual changes
    const hasChanges = updatedNodes.some((node, i) => node !== graph.nodes[i]);
    if (hasChanges) {
      graph.setNodes(updatedNodes);
    }

    // Store node states for transactions
    // If we have modifications, preserve those values instead of overwriting with snapshot
    if (snapshot.node_balances && !hasModifications) {
      const states = {};
      Object.entries(snapshot.node_balances).forEach(([nodeId, balance]) => {
        const fullState = snapshot.node_states?.[nodeId]?.state || {};
        states[nodeId] = {
          balance,
          state: fullState
        };
      });
      setNodeStates(states);
    }

    // Mark as processed
    lastProcessedRef.current = { month: currentMonth, resultId };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentMonth, result]);

  // Run simulation
  const handleRunSimulation = async () => {
    const validation = await validateGraph();
    if (!validation.valid) {
      return;
    }
    await runSimulation();
    setCurrentMonth(1);
    setHasModifications(false);
    setNodeStates({});
  };

  // Play/Pause controls
  const handlePlay = () => {
    if (!result) return;

    if (isPlaying) {
      clearInterval(playInterval);
      setIsPlaying(false);
    } else {
      const interval = setInterval(() => {
        setCurrentMonth((prev) => {
          if (prev >= result.snapshots.length) {
            clearInterval(interval);
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 200);
      setPlayInterval(interval);
      setIsPlaying(true);
    }
  };

  // Skip to end
  const handleSkipToEnd = () => {
    if (result) {
      setCurrentMonth(result.snapshots.length);
    }
  };

  // Step forward
  const handleStep = () => {
    if (result && currentMonth < result.snapshots.length) {
      setCurrentMonth(currentMonth + 1);
    }
  };

  // Restart simulation - clears ledger and resets to month 0
  const handleRestartSimulation = useCallback(async () => {
    // Stop any playing animation
    if (isPlaying) {
      clearInterval(playInterval);
      setIsPlaying(false);
    }

    try {
      // Clear the ledger on the backend
      await axios.post(`${API_BASE}/api/ledger/clear`);

      // Reset all simulation state
      graph.setSimulationResult(null);
      setCurrentMonth(1);
      setHasModifications(false);
      setNodeStates({});

      // Clear simulated balances from nodes
      const resetNodes = graph.nodes.map(node => ({
        ...node,
        data: {
          ...node.data,
          isInactive: false,
          simulatedBalance: undefined,
        },
      }));
      graph.setNodes(resetNodes);

      message.success('Simulation reset. Ledger cleared.');
    } catch (err) {
      message.error('Failed to clear ledger: ' + (err.response?.data?.error || err.message));
    }
  }, [isPlaying, playInterval, graph]);

  // Execute transaction
  const handleExecuteTransaction = useCallback(async (transactionType, params) => {
    setIsTransacting(true);

    try {
      const { nodes, edges } = toApiFormat();
      const { year, month } = getYearMonth(currentMonth, config.start_year, config.start_month);

      const response = await axios.post(`${API_BASE}/api/transaction`, {
        transaction_type: transactionType,
        nodes,
        node_states: nodeStates,
        user_profile: graph.userProfile,
        year,
        month,
        params,
      });

      if (response.data.success) {
        // Update local node states
        const newNodeStates = response.data.node_states;
        setNodeStates(newNodeStates);
        setHasModifications(true);

        // Also update the visual graph nodes with new balances
        // Mark debt/mortgage nodes as inactive if balance is now $0
        const updatedNodes = graph.nodes.map(node => {
          const newState = newNodeStates[node.id];
          if (newState && newState.balance !== undefined) {
            const moduleType = node.data?.moduleType;
            const isDebtType = moduleType === 'debt' || moduleType === 'mortgage';
            // Debt is paid off when balance is 0 or very close (floating point)
            const isPaidOff = isDebtType && Math.abs(newState.balance) < 0.01;

            return {
              ...node,
              data: {
                ...node.data,
                simulatedBalance: newState.balance,
                // Mark as inactive if this debt was just paid off
                isInactive: isPaidOff || node.data.isInactive,
              },
            };
          }
          return node;
        });
        graph.setNodes(updatedNodes);

        message.success(response.data.message);
        return response.data;
      } else {
        message.error(response.data.message || 'Transaction failed');
        return response.data;
      }
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.message;
      message.error(errorMsg);
      return { success: false, message: errorMsg };
    } finally {
      setIsTransacting(false);
    }
  }, [toApiFormat, nodeStates, graph.userProfile, config, currentMonth]);

  // Continue simulation from current point with modified state
  const handleContinueSimulation = useCallback(async () => {
    if (!hasModifications) return;

    graph.setIsSimulating(true);

    try {
      const { nodes, edges } = toApiFormat();

      const response = await axios.post(`${API_BASE}/api/simulate/continue`, {
        nodes,
        edges,
        user_profile: graph.userProfile,
        config: config,
        resume_from_month: currentMonth,
        node_states: nodeStates,
      });

      if (response.data.success) {
        // Merge new snapshots with existing ones
        const existingSnapshots = result.snapshots.slice(0, currentMonth - 1);
        const newSnapshots = response.data.snapshots;
        const mergedSnapshots = [...existingSnapshots, ...newSnapshots];

        graph.setSimulationResult({
          ...result,
          snapshots: mergedSnapshots,
          final_net_worth: response.data.final_net_worth,
        });

        setHasModifications(false);
        message.success(`Simulation continued from month ${currentMonth}`);
      } else {
        message.error(response.data.error || 'Failed to continue simulation');
      }
    } catch (err) {
      message.error(err.response?.data?.error || err.message);
    } finally {
      graph.setIsSimulating(false);
    }
  }, [hasModifications, toApiFormat, graph, config, currentMonth, nodeStates, result]);

  // Get current snapshot
  const currentSnapshot = result?.snapshots[currentMonth - 1];

  // Get current balances - prefer graph nodes' simulatedBalance (most up-to-date after transactions)
  // Fall back to nodeStates or snapshot
  const currentBalances = useMemo(() => {
    const balances = {};

    // First, get balances from snapshot as baseline
    if (currentSnapshot?.node_balances) {
      Object.entries(currentSnapshot.node_balances).forEach(([nodeId, balance]) => {
        balances[nodeId] = balance;
      });
    }

    // Override with nodeStates if we have modifications
    if (hasModifications && nodeStates) {
      Object.entries(nodeStates).forEach(([nodeId, state]) => {
        if (state && state.balance !== undefined) {
          balances[nodeId] = state.balance;
        }
      });
    }

    // Finally, use graph nodes' simulatedBalance as the most current source
    // (this gets updated immediately after transactions)
    graph.nodes.forEach(node => {
      if (node.data?.simulatedBalance !== undefined) {
        balances[node.id] = node.data.simulatedBalance;
      }
    });

    return balances;
  }, [hasModifications, nodeStates, currentSnapshot, graph.nodes]);

  // Prepare flow table data
  const flowTableData = currentSnapshot?.flows.map((flow, index) => ({
    key: index,
    source: flow.source,
    target: flow.target,
    amount: flow.amount,
  })) || [];

  // Prepare balance table data
  const balanceTableData = currentBalances
    ? Object.entries(currentBalances).map(([nodeId, balance]) => ({
        key: nodeId,
        node: nodeId,
        balance,
      }))
    : [];

  // Calculate net worth
  const currentNetWorth = Object.values(currentBalances).reduce((sum, b) => sum + (b || 0), 0);

  // Calculate net worth history for chart
  const netWorthHistory = result?.snapshots.map((snap, i) => ({
    month: i + 1,
    netWorth: snap.net_worth,
  })) || [];

  const { year: currentYear, month: currentMonthOfYear } = result
    ? getYearMonth(currentMonth, config.start_year, config.start_month)
    : { year: config.start_year, month: config.start_month };

  return (
    <Card
      title={
        <Space>
          <LineChartOutlined />
          <span>Simulation</span>
          {hasModifications && (
            <Tag color="orange">Modified</Tag>
          )}
        </Space>
      }
      style={{ height: '100%', overflowY: 'auto' }}
      bodyStyle={{ padding: 16 }}
    >
      {/* Controls */}
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Space wrap>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={handleRunSimulation}
            loading={graph.isSimulating}
          >
            Run Simulation
          </Button>

          {result && (
            <>
              <Button
                icon={isPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                onClick={handlePlay}
              >
                {isPlaying ? 'Pause' : 'Play'}
              </Button>
              <Button icon={<StepForwardOutlined />} onClick={handleStep}>
                Step
              </Button>
              <Button icon={<FastForwardOutlined />} onClick={handleSkipToEnd}>
                End
              </Button>
              <Divider type="vertical" />
              <Tooltip title="Make a manual transaction at this point in time">
                <Button
                  icon={<SwapOutlined />}
                  onClick={() => setTransactionModalOpen(true)}
                >
                  Transaction
                </Button>
              </Tooltip>
              {hasModifications && (
                <Tooltip title="Re-run simulation from this point with your changes">
                  <Button
                    type="primary"
                    ghost
                    icon={<ReloadOutlined />}
                    onClick={handleContinueSimulation}
                    loading={graph.isSimulating}
                  >
                    Continue Sim
                  </Button>
                </Tooltip>
              )}
              <Divider type="vertical" />
              <Tooltip title="Reset to beginning and clear transaction ledger">
                <Button
                  danger
                  icon={<ClearOutlined />}
                  onClick={handleRestartSimulation}
                >
                  Restart
                </Button>
              </Tooltip>
            </>
          )}
        </Space>

        {error && <Alert message={error} type="error" showIcon />}

        {graph.isSimulating && (
          <div style={{ textAlign: 'center', padding: 20 }}>
            <Spin size="large" />
            <div style={{ marginTop: 8 }}>Running simulation...</div>
          </div>
        )}

        {result && !graph.isSimulating && (
          <>
            {/* Timeline Slider */}
            <div style={{ padding: '0 8px' }}>
              <Text type="secondary">
                Month {currentMonth} of {result.snapshots.length}
                {' | '}
                {formatDate(currentMonth, config.start_year, config.start_month)}
              </Text>
              <Slider
                min={1}
                max={result.snapshots.length}
                value={currentMonth}
                onChange={(val) => {
                  setCurrentMonth(val);
                  // Reset modifications if user scrubs to a different month
                  if (hasModifications && val !== currentMonth) {
                    setHasModifications(false);
                  }
                }}
                tooltip={{
                  formatter: (value) =>
                    formatDate(value, config.start_year, config.start_month),
                }}
              />
            </div>

            {/* Summary Stats */}
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title={hasModifications ? "Net Worth (Modified)" : "Net Worth"}
                  value={hasModifications ? currentNetWorth : (currentSnapshot?.net_worth || 0)}
                  precision={0}
                  prefix={<DollarOutlined />}
                  formatter={(value) => formatCurrency(value)}
                  valueStyle={{
                    color: (currentSnapshot?.net_worth || 0) >= 0 ? '#52c41a' : '#f5222d',
                  }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Final Net Worth"
                  value={result.final_net_worth}
                  precision={0}
                  prefix={<DollarOutlined />}
                  formatter={(value) => formatCurrency(value)}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
            </Row>

            {/* Tabs for details */}
            <Tabs defaultActiveKey="balances" size="small">
              <TabPane tab="Balances" key="balances">
                <Table
                  dataSource={balanceTableData}
                  columns={[
                    {
                      title: 'Account',
                      dataIndex: 'node',
                      key: 'node',
                      render: (text) => (
                        <Text style={{ textTransform: 'capitalize' }}>
                          {text.replace(/_/g, ' ')}
                        </Text>
                      ),
                    },
                    {
                      title: 'Balance',
                      dataIndex: 'balance',
                      key: 'balance',
                      align: 'right',
                      render: (value) => (
                        <Text
                          style={{ color: value >= 0 ? '#52c41a' : '#f5222d' }}
                        >
                          {formatCurrency(value)}
                        </Text>
                      ),
                    },
                  ]}
                  size="small"
                  pagination={false}
                />
              </TabPane>

              <TabPane tab="Flows" key="flows">
                <Table
                  dataSource={flowTableData}
                  columns={[
                    { title: 'From', dataIndex: 'source', key: 'source' },
                    { title: 'To', dataIndex: 'target', key: 'target' },
                    {
                      title: 'Amount',
                      dataIndex: 'amount',
                      key: 'amount',
                      align: 'right',
                      render: (value) => formatCurrency(value),
                    },
                  ]}
                  size="small"
                  pagination={false}
                  locale={{ emptyText: 'No flows this month' }}
                />
              </TabPane>

              <TabPane tab="Events" key="events">
                {currentSnapshot?.events.length > 0 ? (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {currentSnapshot.events.map((event, i) => (
                      <Tag key={i} color="blue">
                        {event}
                      </Tag>
                    ))}
                  </Space>
                ) : (
                  <Text type="secondary">No events this month</Text>
                )}
              </TabPane>

              <TabPane tab="History" key="history">
                <div style={{ height: 150, padding: '8px 0' }}>
                  {/* Simple text-based chart */}
                  <Row gutter={8}>
                    {netWorthHistory
                      .filter((_, i) => i % 12 === 0 || i === currentMonth - 1)
                      .slice(0, 10)
                      .map((point, i) => (
                        <Col key={i} span={2}>
                          <Tooltip title={`Month ${point.month}: ${formatCurrency(point.netWorth)}`}>
                            <Progress
                              type="line"
                              percent={Math.min(
                                100,
                                Math.max(
                                  0,
                                  (point.netWorth /
                                    Math.max(...netWorthHistory.map((p) => p.netWorth))) *
                                    100
                                )
                              )}
                              showInfo={false}
                              strokeColor={point.netWorth >= 0 ? '#52c41a' : '#f5222d'}
                              trailColor="#f0f0f0"
                              strokeWidth={20}
                              style={{ transform: 'rotate(-90deg)', height: 40 }}
                            />
                          </Tooltip>
                        </Col>
                      ))}
                  </Row>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    Net worth over time (yearly)
                  </Text>
                </div>
              </TabPane>
            </Tabs>
          </>
        )}
      </Space>

      {/* Transaction Modal */}
      <TransactionModal
        open={transactionModalOpen}
        onClose={() => setTransactionModalOpen(false)}
        onExecute={handleExecuteTransaction}
        nodes={graph.nodes}
        currentBalances={currentBalances}
        currentMonth={currentMonthOfYear}
        currentYear={currentYear}
        isLoading={isTransacting}
      />
    </Card>
  );
}

export default SimulationPanel;
