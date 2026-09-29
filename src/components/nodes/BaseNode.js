import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { Card, Typography, Tag } from 'antd';
import {
  DollarOutlined,
  BankOutlined,
  StockOutlined,
  HomeOutlined,
  CreditCardOutlined,
  WalletOutlined,
  ShoppingOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;

// Node type configurations
const nodeTypeConfig = {
  salary: {
    icon: DollarOutlined,
    color: '#52c41a',
    bgColor: '#f6ffed',
    borderColor: '#b7eb8f',
    category: 'Income',
  },
  savings_account: {
    icon: BankOutlined,
    color: '#1890ff',
    bgColor: '#e6f7ff',
    borderColor: '#91d5ff',
    category: 'Account',
  },
  stock_portfolio: {
    icon: StockOutlined,
    color: '#722ed1',
    bgColor: '#f9f0ff',
    borderColor: '#d3adf7',
    category: 'Investment',
  },
  four_oh_one_k: {
    icon: WalletOutlined,
    color: '#eb2f96',
    bgColor: '#fff0f6',
    borderColor: '#ffadd2',
    category: 'Investment',
  },
  five_twenty_nine: {
    icon: BankOutlined,
    color: '#13c2c2',
    bgColor: '#e6fffb',
    borderColor: '#87e8de',
    category: 'Investment',
  },
  ira: {
    icon: WalletOutlined,
    color: '#fa8c16',
    bgColor: '#fff7e6',
    borderColor: '#ffd591',
    category: 'Investment',
  },
  real_estate: {
    icon: HomeOutlined,
    color: '#a0522d',
    bgColor: '#faf0e6',
    borderColor: '#d2b48c',
    category: 'Investment',
  },
  mortgage: {
    icon: CreditCardOutlined,
    color: '#f5222d',
    bgColor: '#fff1f0',
    borderColor: '#ffa39e',
    category: 'Debt',
  },
  debt: {
    icon: CreditCardOutlined,
    color: '#cf1322',
    bgColor: '#fff1f0',
    borderColor: '#ffa39e',
    category: 'Debt',
  },
  expense: {
    icon: ShoppingOutlined,
    color: '#fa541c',
    bgColor: '#fff2e8',
    borderColor: '#ffbb96',
    category: 'Expense',
  },
};

// Format currency
const formatCurrency = (value) => {
  if (value === undefined || value === null) return '-';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

function BaseNode({ data, selected }) {
  const config = nodeTypeConfig[data.moduleType] || nodeTypeConfig.savings_account;
  const Icon = config.icon;
  const isInactive = data.isInactive === true;

  // Get the display value based on module type
  const getDisplayValue = () => {
    const c = data.config || {};
    switch (data.moduleType) {
      case 'salary':
        return formatCurrency(c.annual_salary);
      case 'savings_account':
        return formatCurrency(c.initial_balance);
      case 'stock_portfolio':
        return formatCurrency(c.initial_value);
      case 'four_oh_one_k':
      case 'ira':
      case 'five_twenty_nine':
        return formatCurrency(c.initial_balance);
      case 'real_estate':
        return formatCurrency(c.purchase_price);
      case 'mortgage':
        return formatCurrency(c.original_principal);
      case 'debt':
        return formatCurrency(c.current_balance);
      case 'expense':
        return formatCurrency(c.monthly_amount || c.annual_amount || 0);
      default:
        return '-';
    }
  };

  // Get secondary info
  const getSecondaryInfo = () => {
    const c = data.config || {};
    switch (data.moduleType) {
      case 'salary':
        return c.income_type === '1099' ? '1099' : 'W2';
      case 'savings_account':
        return `${c.apy || 0}% APY`;
      case 'stock_portfolio':
        return `${c.expected_annual_return || 7}% return`;
      case 'four_oh_one_k':
        return c.account_type === 'roth' ? 'Roth' : 'Traditional';
      case 'ira':
        return c.account_type === 'roth' ? 'Roth IRA' : 'Traditional IRA';
      case 'five_twenty_nine':
        return c.beneficiary || '529 Plan';
      case 'real_estate':
        return `${c.value_appreciation_per_year_pct || 3}% appreciation`;
      case 'mortgage':
        return `${c.interest_rate_pct || 6.5}% rate`;
      case 'debt':
        const debtTypes = {
          student_loan: 'Student',
          car_loan: 'Car',
          personal_loan: 'Personal',
          credit_card: 'Credit Card',
        };
        return debtTypes[c.debt_type] || `${c.interest_rate_pct || 6}%`;
      case 'expense':
        const categories = {
          childcare: 'Childcare',
          education: 'Education',
          utilities: 'Utilities',
          subscription: 'Subscription',
          healthcare: 'Healthcare',
          transportation: 'Transport',
          food: 'Food',
          entertainment: 'Entertainment',
          other: 'Other',
        };
        return categories[c.category] || c.expense_type || 'Expense';
      default:
        return '';
    }
  };

  return (
    <div
      style={{
        minWidth: 180,
        maxWidth: 220,
      }}
    >
      {/* Input handle */}
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: config.color,
          width: 10,
          height: 10,
        }}
      />

      <Card
        size="small"
        style={{
          backgroundColor: isInactive ? '#f5f5f5' : config.bgColor,
          borderColor: isInactive ? '#d9d9d9' : (selected ? config.color : config.borderColor),
          borderWidth: selected ? 2 : 1,
          borderRadius: 8,
          boxShadow: selected ? `0 0 0 2px ${config.color}40` : 'none',
          opacity: isInactive ? 0.6 : 1,
        }}
        bodyStyle={{ padding: '8px 12px' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <Icon style={{ fontSize: 18, color: isInactive ? '#bfbfbf' : config.color }} />
          <Text strong style={{ flex: 1, fontSize: 13, color: isInactive ? '#8c8c8c' : 'inherit' }}>
            {data.config?.name || data.label || data.moduleType}
          </Text>
          {isInactive && (
            <Tag style={{ fontSize: 9, padding: '0 4px', margin: 0, backgroundColor: '#f0f0f0', border: '1px solid #d9d9d9', color: '#8c8c8c' }}>
              Ended
            </Tag>
          )}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text style={{ fontSize: 16, fontWeight: 600, color: config.color }}>
            {getDisplayValue()}
          </Text>
          <Tag
            style={{
              fontSize: 10,
              padding: '0 4px',
              margin: 0,
              backgroundColor: 'transparent',
              borderColor: config.borderColor,
              color: config.color,
            }}
          >
            {getSecondaryInfo()}
          </Tag>
        </div>

        {/* Show simulation balance if available */}
        {data.simulatedBalance !== undefined && (
          <div style={{ marginTop: 4, borderTop: `1px dashed ${config.borderColor}`, paddingTop: 4 }}>
            <Text type="secondary" style={{ fontSize: 11 }}>
              Current: {formatCurrency(data.simulatedBalance)}
            </Text>
          </div>
        )}
      </Card>

      {/* Output handle */}
      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: config.color,
          width: 10,
          height: 10,
        }}
      />
    </div>
  );
}

export default memo(BaseNode);
