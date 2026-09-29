import React, { useState, useMemo } from 'react';
import {
  Modal,
  Form,
  Select,
  InputNumber,
  Button,
  Space,
  Typography,
  Alert,
  Divider,
  Card,
  Statistic,
  Row,
  Col,
  Tag,
} from 'antd';
import {
  DollarOutlined,
  SwapOutlined,
  CreditCardOutlined,
  StockOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;
const { Option } = Select;

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

function TransactionModal({
  open,
  onClose,
  onExecute,
  nodes,
  currentBalances,
  currentMonth,
  currentYear,
  isLoading,
}) {
  const [form] = Form.useForm();
  const [transactionType, setTransactionType] = useState('sell_stocks');
  const [result, setResult] = useState(null);

  // Categorize nodes by type
  const nodesByType = useMemo(() => {
    const stocks = [];
    const accounts = [];
    const debts = [];

    nodes.forEach((node) => {
      const type = node.data?.moduleType;
      const balance = currentBalances?.[node.id] || 0;
      const nodeInfo = {
        id: node.id,
        name: node.data?.config?.name || node.id,
        type,
        balance,
      };

      if (type === 'stock_portfolio') {
        stocks.push(nodeInfo);
      } else if (type === 'savings_account') {
        accounts.push(nodeInfo);
      } else if (type === 'debt' || type === 'mortgage') {
        debts.push(nodeInfo);
      }
    });

    return { stocks, accounts, debts };
  }, [nodes, currentBalances]);

  const handleSubmit = async (values) => {
    setResult(null);

    const params = {};
    if (transactionType === 'sell_stocks') {
      params.source_node = values.stockNode;
      params.amount = values.amount;
      params.destination_node = values.destinationAccount;
    } else if (transactionType === 'pay_debt') {
      params.source_node = values.sourceAccount;
      params.target_node = values.debtNode;
      params.amount = values.payFull ? 'full' : values.amount;
    } else if (transactionType === 'transfer') {
      params.source_node = values.sourceAccount;
      params.target_node = values.targetAccount;
      params.amount = values.amount;
    }

    const txResult = await onExecute(transactionType, params);
    setResult(txResult);
  };

  const handleClose = () => {
    setResult(null);
    form.resetFields();
    onClose();
  };

  const selectedStockBalance = Form.useWatch('stockNode', form)
    ? currentBalances?.[form.getFieldValue('stockNode')] || 0
    : 0;

  const selectedDebtBalance = Form.useWatch('debtNode', form)
    ? Math.abs(currentBalances?.[form.getFieldValue('debtNode')] || 0)
    : 0;

  const selectedSourceBalance = Form.useWatch('sourceAccount', form)
    ? currentBalances?.[form.getFieldValue('sourceAccount')] || 0
    : 0;

  return (
    <Modal
      title={
        <Space>
          <SwapOutlined />
          <span>Manual Transaction</span>
          <Tag color="blue">
            {currentMonth}/{currentYear}
          </Tag>
        </Space>
      }
      open={open}
      onCancel={handleClose}
      footer={null}
      width={600}
    >
      {/* Transaction Type Selection */}
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">Transaction Type:</Text>
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <Button
            type={transactionType === 'sell_stocks' ? 'primary' : 'default'}
            icon={<StockOutlined />}
            onClick={() => {
              setTransactionType('sell_stocks');
              form.resetFields();
              setResult(null);
            }}
          >
            Sell Stocks
          </Button>
          <Button
            type={transactionType === 'pay_debt' ? 'primary' : 'default'}
            icon={<CreditCardOutlined />}
            onClick={() => {
              setTransactionType('pay_debt');
              form.resetFields();
              setResult(null);
            }}
          >
            Pay Debt
          </Button>
          <Button
            type={transactionType === 'transfer' ? 'primary' : 'default'}
            icon={<DollarOutlined />}
            onClick={() => {
              setTransactionType('transfer');
              form.resetFields();
              setResult(null);
            }}
          >
            Transfer
          </Button>
        </div>
      </div>

      <Divider />

      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        {/* Sell Stocks Form */}
        {transactionType === 'sell_stocks' && (
          <>
            <Form.Item
              name="stockNode"
              label="Stock Portfolio"
              rules={[{ required: true, message: 'Select a stock portfolio' }]}
            >
              <Select placeholder="Select stock portfolio">
                {nodesByType.stocks.map((node) => (
                  <Option key={node.id} value={node.id}>
                    {node.name} ({formatCurrency(node.balance)})
                  </Option>
                ))}
              </Select>
            </Form.Item>

            {selectedStockBalance > 0 && (
              <Card size="small" style={{ marginBottom: 16 }}>
                <Statistic
                  title="Available to Sell"
                  value={selectedStockBalance}
                  precision={0}
                  prefix="$"
                  valueStyle={{ color: '#722ed1' }}
                />
              </Card>
            )}

            <Form.Item
              name="amount"
              label="Amount to Sell"
              rules={[
                { required: true, message: 'Enter amount' },
                {
                  validator: (_, value) =>
                    value <= selectedStockBalance
                      ? Promise.resolve()
                      : Promise.reject('Amount exceeds available balance'),
                },
              ]}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                max={selectedStockBalance}
                formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                parser={(value) => value.replace(/\$\s?|(,*)/g, '')}
              />
            </Form.Item>

            <Form.Item
              name="destinationAccount"
              label="Deposit Proceeds To"
              rules={[{ required: true, message: 'Select destination account' }]}
            >
              <Select placeholder="Select destination account">
                {nodesByType.accounts.map((node) => (
                  <Option key={node.id} value={node.id}>
                    {node.name} ({formatCurrency(node.balance)})
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Alert
              message="Capital Gains Tax"
              description="Selling stocks may trigger capital gains tax. Short-term gains (held < 1 year) are taxed as ordinary income. Long-term gains have preferential rates."
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
          </>
        )}

        {/* Pay Debt Form */}
        {transactionType === 'pay_debt' && (
          <>
            <Form.Item
              name="sourceAccount"
              label="Pay From Account"
              rules={[{ required: true, message: 'Select source account' }]}
            >
              <Select placeholder="Select account">
                {nodesByType.accounts.map((node) => (
                  <Option key={node.id} value={node.id}>
                    {node.name} ({formatCurrency(node.balance)})
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name="debtNode"
              label="Debt to Pay"
              rules={[{ required: true, message: 'Select debt' }]}
            >
              <Select placeholder="Select debt">
                {nodesByType.debts.map((node) => (
                  <Option key={node.id} value={node.id}>
                    {node.name} ({formatCurrency(Math.abs(node.balance))} owed)
                  </Option>
                ))}
              </Select>
            </Form.Item>

            {selectedDebtBalance > 0 && (
              <Card size="small" style={{ marginBottom: 16 }}>
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title="Debt Balance"
                      value={selectedDebtBalance}
                      precision={0}
                      prefix="$"
                      valueStyle={{ color: '#f5222d' }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="Available Funds"
                      value={selectedSourceBalance}
                      precision={0}
                      prefix="$"
                      valueStyle={{ color: '#52c41a' }}
                    />
                  </Col>
                </Row>
              </Card>
            )}

            <Form.Item name="payFull" valuePropName="checked">
              <Button
                type="dashed"
                block
                onClick={() => {
                  const payoffAmount = Math.min(selectedDebtBalance, selectedSourceBalance);
                  form.setFieldsValue({ amount: payoffAmount, payFull: true });
                }}
                disabled={selectedSourceBalance < selectedDebtBalance}
              >
                Pay Off in Full ({formatCurrency(selectedDebtBalance)})
              </Button>
            </Form.Item>

            <Form.Item
              name="amount"
              label="Or Enter Custom Amount"
              rules={[
                {
                  validator: (_, value) => {
                    if (!value && !form.getFieldValue('payFull')) {
                      return Promise.reject('Enter amount or select Pay Off in Full');
                    }
                    if (value > selectedSourceBalance) {
                      return Promise.reject('Amount exceeds available funds');
                    }
                    return Promise.resolve();
                  },
                },
              ]}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                max={Math.min(selectedDebtBalance, selectedSourceBalance)}
                formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                parser={(value) => value.replace(/\$\s?|(,*)/g, '')}
              />
            </Form.Item>
          </>
        )}

        {/* Transfer Form */}
        {transactionType === 'transfer' && (
          <>
            <Form.Item
              name="sourceAccount"
              label="From Account"
              rules={[{ required: true, message: 'Select source account' }]}
            >
              <Select placeholder="Select source">
                {nodesByType.accounts.map((node) => (
                  <Option key={node.id} value={node.id}>
                    {node.name} ({formatCurrency(node.balance)})
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name="targetAccount"
              label="To Account"
              rules={[{ required: true, message: 'Select target account' }]}
            >
              <Select placeholder="Select target">
                {nodesByType.accounts.map((node) => (
                  <Option key={node.id} value={node.id}>
                    {node.name} ({formatCurrency(node.balance)})
                  </Option>
                ))}
              </Select>
            </Form.Item>

            {selectedSourceBalance > 0 && (
              <Card size="small" style={{ marginBottom: 16 }}>
                <Statistic
                  title="Available to Transfer"
                  value={selectedSourceBalance}
                  precision={0}
                  prefix="$"
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            )}

            <Form.Item
              name="amount"
              label="Amount"
              rules={[
                { required: true, message: 'Enter amount' },
                {
                  validator: (_, value) =>
                    value <= selectedSourceBalance
                      ? Promise.resolve()
                      : Promise.reject('Amount exceeds available balance'),
                },
              ]}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                max={selectedSourceBalance}
                formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                parser={(value) => value.replace(/\$\s?|(,*)/g, '')}
              />
            </Form.Item>
          </>
        )}

        {/* Result Display */}
        {result && (
          <div style={{ marginBottom: 16 }}>
            {result.success ? (
              <Alert
                message="Transaction Successful"
                description={
                  <div>
                    <p>{result.message}</p>
                    {result.tax_implications?.total_estimated_tax > 0 && (
                      <div style={{ marginTop: 8 }}>
                        <Text strong>Estimated Tax Impact:</Text>
                        <ul style={{ margin: '8px 0', paddingLeft: 20 }}>
                          {result.tax_implications.short_term_federal > 0 && (
                            <li>
                              Short-term federal: {formatCurrency(result.tax_implications.short_term_federal)}
                            </li>
                          )}
                          {result.tax_implications.long_term_federal > 0 && (
                            <li>
                              Long-term federal: {formatCurrency(result.tax_implications.long_term_federal)}
                            </li>
                          )}
                          {result.tax_implications.state_tax > 0 && (
                            <li>State tax: {formatCurrency(result.tax_implications.state_tax)}</li>
                          )}
                          <li>
                            <strong>
                              Total estimated tax: {formatCurrency(result.tax_implications.total_estimated_tax)}
                            </strong>
                          </li>
                        </ul>
                      </div>
                    )}
                    {result.events?.map((event, i) => (
                      <Tag key={i} color="green" style={{ marginTop: 4 }}>
                        {event}
                      </Tag>
                    ))}
                  </div>
                }
                type="success"
                showIcon
              />
            ) : (
              <Alert message="Transaction Failed" description={result.message} type="error" showIcon />
            )}
          </div>
        )}

        {/* Actions */}
        <Form.Item style={{ marginBottom: 0, marginTop: 16 }}>
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={handleClose}>Cancel</Button>
            <Button type="primary" htmlType="submit" loading={isLoading}>
              Execute Transaction
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
}

export default TransactionModal;
