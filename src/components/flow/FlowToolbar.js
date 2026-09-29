import React from 'react';
import { Card, Typography, Space, Button, Tooltip, Divider } from 'antd';
import {
  DollarOutlined,
  BankOutlined,
  StockOutlined,
  HomeOutlined,
  CreditCardOutlined,
  WalletOutlined,
  PlusOutlined,
  ShoppingOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;

// Node type definitions for the toolbar
const nodeCategories = [
  {
    title: 'Income',
    items: [
      {
        type: 'salary',
        label: 'Salary',
        icon: DollarOutlined,
        color: '#52c41a',
        description: 'W2 or 1099 income',
      },
    ],
  },
  {
    title: 'Accounts',
    items: [
      {
        type: 'savings_account',
        label: 'Savings',
        icon: BankOutlined,
        color: '#1890ff',
        description: 'Savings or checking account',
      },
    ],
  },
  {
    title: 'Investments',
    items: [
      {
        type: 'stock_portfolio',
        label: 'Stocks',
        icon: StockOutlined,
        color: '#722ed1',
        description: 'Stock portfolio',
      },
      {
        type: 'four_oh_one_k',
        label: '401(k)',
        icon: WalletOutlined,
        color: '#eb2f96',
        description: 'Employer retirement',
      },
      {
        type: 'ira',
        label: 'IRA',
        icon: WalletOutlined,
        color: '#fa8c16',
        description: 'Traditional or Roth',
      },
      {
        type: 'five_twenty_nine',
        label: '529',
        icon: BankOutlined,
        color: '#13c2c2',
        description: 'Education savings',
      },
      {
        type: 'real_estate',
        label: 'Real Estate',
        icon: HomeOutlined,
        color: '#a0522d',
        description: 'Rental property',
      },
    ],
  },
  {
    title: 'Debt',
    items: [
      {
        type: 'mortgage',
        label: 'Mortgage',
        icon: CreditCardOutlined,
        color: '#f5222d',
        description: 'Home loan',
      },
      {
        type: 'debt',
        label: 'Loan/Debt',
        icon: CreditCardOutlined,
        color: '#cf1322',
        description: 'Student, car, or personal loan',
      },
    ],
  },
  {
    title: 'Expenses',
    items: [
      {
        type: 'expense',
        label: 'Expense',
        icon: ShoppingOutlined,
        color: '#fa541c',
        description: 'Daycare, utilities, subscriptions',
      },
    ],
  },
];

function FlowToolbar({ onAddNode }) {
  const onDragStart = (event, nodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <Card
      size="small"
      style={{
        width: 180,
        height: '100%',
        overflowY: 'auto',
        borderRadius: 0,
        borderRight: '1px solid #f0f0f0',
      }}
      bodyStyle={{ padding: '12px 8px' }}
    >
      <Title level={5} style={{ marginBottom: 12, paddingLeft: 4 }}>
        Add Nodes
      </Title>
      <Text type="secondary" style={{ fontSize: 11, paddingLeft: 4 }}>
        Drag to canvas or click to add
      </Text>

      {nodeCategories.map((category, catIndex) => (
        <div key={category.title} style={{ marginTop: catIndex > 0 ? 16 : 12 }}>
          <Text
            type="secondary"
            style={{
              fontSize: 11,
              textTransform: 'uppercase',
              letterSpacing: 1,
              paddingLeft: 4,
            }}
          >
            {category.title}
          </Text>

          <Space direction="vertical" style={{ width: '100%', marginTop: 6 }} size={4}>
            {category.items.map((item) => {
              const Icon = item.icon;
              return (
                <Tooltip
                  key={item.type}
                  title={item.description}
                  placement="right"
                  mouseEnterDelay={0.5}
                >
                  <div
                    draggable
                    onDragStart={(e) => onDragStart(e, item.type)}
                    onClick={() => onAddNode(item.type)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '8px 10px',
                      borderRadius: 6,
                      cursor: 'grab',
                      backgroundColor: '#fafafa',
                      border: '1px solid #f0f0f0',
                      transition: 'all 0.2s',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = `${item.color}10`;
                      e.currentTarget.style.borderColor = item.color;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = '#fafafa';
                      e.currentTarget.style.borderColor = '#f0f0f0';
                    }}
                  >
                    <Icon style={{ fontSize: 16, color: item.color }} />
                    <Text style={{ fontSize: 12, flex: 1 }}>{item.label}</Text>
                    <PlusOutlined style={{ fontSize: 10, color: '#bfbfbf' }} />
                  </div>
                </Tooltip>
              );
            })}
          </Space>
        </div>
      ))}
    </Card>
  );
}

export default FlowToolbar;
