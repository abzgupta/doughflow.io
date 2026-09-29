import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Space,
  Typography,
  Statistic,
  Row,
  Col,
  Descriptions,
  Divider,
  Tag,
  Alert,
  Tooltip,
  Progress,
} from 'antd';
import {
  CalculatorOutlined,
  DollarOutlined,
  PercentageOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useGraph } from '../../context/GraphContext';
import { useGraphState } from '../../hooks/useGraphState';

const { Title, Text } = Typography;

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

// Format percent
const formatPercent = (value) => {
  if (value === undefined || value === null) return '-';
  return `${(value * 100).toFixed(1)}%`;
};

function TaxSummaryPanel() {
  const graph = useGraph();
  const { calculateTax, error } = useGraphState();
  const [taxResult, setTaxResult] = useState(null);
  const [isCalculating, setIsCalculating] = useState(false);

  // Extract income from simulation result
  const getIncomeFromSimulation = () => {
    if (!graph.simulationResult) return null;

    // Aggregate annual income from all nodes
    const annualSummaries = graph.simulationResult.annual_summaries || {};
    const firstYear = Object.keys(annualSummaries)[0];
    const summary = annualSummaries[firstYear] || {};

    // Default to user profile salary if no simulation
    return {
      wages: graph.userProfile.annual_salary || 150000,
      dividends_qualified: 0,
      capital_gains_long: 0,
      interest: 0,
    };
  };

  // Calculate tax
  const handleCalculateTax = async () => {
    setIsCalculating(true);
    const income = getIncomeFromSimulation() || {
      wages: graph.userProfile.annual_salary || 150000,
    };

    const result = await calculateTax(
      income,
      {}, // deductions - would come from simulation
      {}  // credits
    );

    if (result) {
      setTaxResult(result);
    }
    setIsCalculating(false);
  };

  return (
    <Card
      title={
        <Space>
          <CalculatorOutlined />
          <span>Tax Summary</span>
        </Space>
      }
      style={{ height: '100%', overflowY: 'auto' }}
      bodyStyle={{ padding: 16 }}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* User Profile Summary */}
        <div>
          <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
            Filing Status
          </Text>
          <div>
            <Tag color="blue">
              {graph.userProfile.filing_status?.replace('_', ' ').toUpperCase() || 'SINGLE'}
            </Tag>
            <Tag>{graph.userProfile.state || 'CA'}</Tag>
          </div>
        </div>

        <Button
          type="primary"
          icon={<CalculatorOutlined />}
          onClick={handleCalculateTax}
          loading={isCalculating}
          block
        >
          Calculate Tax
        </Button>

        {error && <Alert message={error} type="error" showIcon />}

        {taxResult && (
          <>
            <Divider style={{ margin: '12px 0' }} />

            {/* Federal Tax Summary */}
            <div>
              <Title level={5} style={{ marginBottom: 12 }}>
                Federal Tax
              </Title>

              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Statistic
                    title="Gross Income"
                    value={taxResult.federal.gross_income}
                    precision={0}
                    formatter={(v) => formatCurrency(v)}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="AGI"
                    value={taxResult.federal.adjusted_gross_income}
                    precision={0}
                    formatter={(v) => formatCurrency(v)}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="Taxable Income"
                    value={taxResult.federal.taxable_income}
                    precision={0}
                    formatter={(v) => formatCurrency(v)}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="Federal Tax"
                    value={taxResult.federal.total_tax}
                    precision={0}
                    formatter={(v) => formatCurrency(v)}
                    valueStyle={{ color: '#f5222d' }}
                  />
                </Col>
              </Row>

              <Divider style={{ margin: '12px 0' }} />

              <Descriptions size="small" column={1}>
                <Descriptions.Item label="Effective Rate">
                  <Text strong>{formatPercent(taxResult.federal.effective_rate)}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="Marginal Rate">
                  <Text strong>{formatPercent(taxResult.federal.marginal_rate)}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="Deduction Type">
                  <Tag color="green">
                    {taxResult.federal.breakdown?.deduction_type?.toUpperCase() || 'STANDARD'}
                  </Tag>
                </Descriptions.Item>
              </Descriptions>

              {/* Tax Breakdown */}
              {taxResult.federal.capital_gains_tax > 0 && (
                <Descriptions size="small" column={1} style={{ marginTop: 12 }}>
                  <Descriptions.Item label="Ordinary Income Tax">
                    {formatCurrency(taxResult.federal.ordinary_income_tax)}
                  </Descriptions.Item>
                  <Descriptions.Item label="Capital Gains Tax">
                    {formatCurrency(taxResult.federal.capital_gains_tax)}
                  </Descriptions.Item>
                </Descriptions>
              )}
            </div>

            <Divider style={{ margin: '12px 0' }} />

            {/* State Tax Summary */}
            <div>
              <Title level={5} style={{ marginBottom: 12 }}>
                State Tax ({taxResult.state.state})
              </Title>

              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title="State Tax"
                    value={taxResult.state.tax_liability}
                    precision={0}
                    formatter={(v) => formatCurrency(v)}
                    valueStyle={{ color: '#fa8c16' }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="Effective Rate"
                    value={taxResult.state.effective_rate}
                    precision={1}
                    formatter={(v) => formatPercent(v)}
                  />
                </Col>
              </Row>
            </div>

            <Divider style={{ margin: '12px 0' }} />

            {/* Total Summary */}
            <div style={{ background: '#f5f5f5', padding: 12, borderRadius: 8 }}>
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title="Total Tax"
                    value={taxResult.total_tax}
                    precision={0}
                    formatter={(v) => formatCurrency(v)}
                    valueStyle={{ color: '#f5222d', fontWeight: 'bold' }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="Combined Rate"
                    value={taxResult.total_effective_rate}
                    precision={1}
                    formatter={(v) => formatPercent(v)}
                    prefix={<PercentageOutlined />}
                  />
                </Col>
              </Row>

              <Progress
                percent={Math.round(taxResult.total_effective_rate * 100)}
                strokeColor={{
                  '0%': '#52c41a',
                  '50%': '#faad14',
                  '100%': '#f5222d',
                }}
                format={(percent) => `${percent}% of income`}
                style={{ marginTop: 12 }}
              />
            </div>

            {/* Refund/Owed */}
            {(taxResult.federal.refund > 0 || taxResult.federal.amount_owed > 0) && (
              <Alert
                type={taxResult.federal.refund > 0 ? 'success' : 'warning'}
                icon={taxResult.federal.refund > 0 ? <CheckCircleOutlined /> : <InfoCircleOutlined />}
                message={
                  taxResult.federal.refund > 0
                    ? `Estimated Refund: ${formatCurrency(taxResult.federal.refund)}`
                    : `Estimated Amount Owed: ${formatCurrency(taxResult.federal.amount_owed)}`
                }
                showIcon
              />
            )}
          </>
        )}

        {!taxResult && !isCalculating && (
          <div style={{ textAlign: 'center', padding: 20 }}>
            <Text type="secondary">
              Click "Calculate Tax" to see your estimated tax liability
            </Text>
          </div>
        )}
      </Space>
    </Card>
  );
}

export default TaxSummaryPanel;
