import React, { useState, useEffect } from 'react';
import {
  Drawer,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Button,
  Space,
  Typography,
  Divider,
  Collapse,
  Popconfirm,
  Statistic,
  Card,
  Tag,
} from 'antd';
import { DeleteOutlined, SaveOutlined, DollarOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;
const { Option } = Select;
const { Panel } = Collapse;

// Common schedule section for all modules
const scheduleSection = {
  title: 'Schedule',
  fields: [
    { name: 'start_year', label: 'Start Year', type: 'year' },
    { name: 'start_month', label: 'Start Month', type: 'month' },
    { name: 'end_year', label: 'End Year (0 = never)', type: 'year' },
    { name: 'end_month', label: 'End Month', type: 'month' },
  ],
};

// Form field configurations for each module type
const formConfigs = {
  salary: {
    title: 'Salary / Income',
    sections: [
      {
        title: 'Basic Info',
        fields: [
          { name: 'name', label: 'Name', type: 'text', required: true },
          {
            name: 'income_type',
            label: 'Income Type',
            type: 'select',
            options: [
              { value: 'w2', label: 'W2 Employee' },
              { value: '1099', label: '1099 Contractor' },
            ],
          },
          { name: 'annual_salary', label: 'Annual Salary', type: 'currency', required: true },
          {
            name: 'pay_frequency',
            label: 'Pay Frequency',
            type: 'select',
            options: [
              { value: 'monthly', label: 'Monthly' },
              { value: 'semi-monthly', label: 'Semi-Monthly' },
              { value: 'bi-weekly', label: 'Bi-Weekly' },
            ],
          },
        ],
      },
      {
        title: 'Growth & Deductions',
        fields: [
          { name: 'annual_raise_pct', label: 'Annual Raise %', type: 'percent' },
          { name: 'federal_withholding_pct', label: 'Federal Withholding %', type: 'percent' },
          { name: 'state_withholding_pct', label: 'State Withholding %', type: 'percent' },
          { name: 'pre_tax_401k_pct', label: '401(k) Contribution %', type: 'percent' },
        ],
      },
      {
        title: 'Bonus',
        fields: [{ name: 'annual_bonus', label: 'Annual Bonus', type: 'currency' }],
      },
      scheduleSection,
    ],
  },
  savings_account: {
    title: 'Savings / Checking Account',
    sections: [
      {
        title: 'Account Info',
        fields: [
          { name: 'name', label: 'Account Name', type: 'text', required: true },
          {
            name: 'account_type',
            label: 'Account Type',
            type: 'select',
            options: [
              { value: 'checking', label: 'Checking' },
              { value: 'savings', label: 'Savings' },
              { value: 'emergency_fund', label: 'Emergency Fund' },
              { value: 'money_market', label: 'Money Market' },
            ],
          },
          { name: 'initial_balance', label: 'Initial Balance', type: 'currency' },
          { name: 'apy', label: 'APY %', type: 'percent' },
        ],
      },
      {
        title: 'Limits',
        fields: [
          { name: 'minimum_balance', label: 'Minimum Balance', type: 'currency' },
          { name: 'target_balance', label: 'Target Balance', type: 'currency' },
          { name: 'low_balance_fee', label: 'Low Balance Fee', type: 'currency' },
        ],
      },
      scheduleSection,
    ],
  },
  stock_portfolio: {
    title: 'Stock Portfolio',
    sections: [
      {
        title: 'Portfolio Info',
        fields: [
          { name: 'name', label: 'Portfolio Name', type: 'text', required: true },
          { name: 'initial_value', label: 'Initial Invested Value', type: 'currency' },
          { name: 'initial_cash', label: 'Initial Cash Balance', type: 'currency' },
          { name: 'expected_annual_return', label: 'Expected Return %', type: 'percent' },
          { name: 'dividend_yield', label: 'Dividend Yield %', type: 'percent' },
        ],
      },
      {
        title: 'Options',
        fields: [
          { name: 'dividend_reinvest', label: 'Reinvest Dividends', type: 'switch' },
          { name: 'auto_invest_contributions', label: 'Auto-Invest Contributions', type: 'switch' },
          { name: 'expense_ratio', label: 'Expense Ratio %', type: 'percent' },
          { name: 'target_cash_reserve', label: 'Target Cash Reserve', type: 'currency' },
        ],
      },
      scheduleSection,
    ],
  },
  four_oh_one_k: {
    title: '401(k) Account',
    sections: [
      {
        title: 'Account Info',
        fields: [
          { name: 'name', label: 'Account Name', type: 'text', required: true },
          {
            name: 'account_type',
            label: 'Account Type',
            type: 'select',
            options: [
              { value: 'traditional', label: 'Traditional (Pre-Tax)' },
              { value: 'roth', label: 'Roth (Post-Tax)' },
            ],
          },
          { name: 'initial_balance', label: 'Initial Balance', type: 'currency' },
          { name: 'expected_annual_return', label: 'Expected Return %', type: 'percent' },
        ],
      },
      {
        title: 'Employer Match',
        fields: [
          { name: 'employer_match_pct', label: 'Match Rate %', type: 'percent' },
          { name: 'employer_match_limit', label: 'Match Limit (% of Salary)', type: 'percent' },
        ],
      },
      {
        title: 'Vesting',
        fields: [
          {
            name: 'vesting_type',
            label: 'Vesting Type',
            type: 'select',
            options: [
              { value: 'immediate', label: 'Immediate' },
              { value: 'cliff', label: 'Cliff' },
              { value: 'graded', label: 'Graded' },
            ],
          },
          { name: 'vesting_years', label: 'Vesting Years', type: 'number' },
        ],
      },
      scheduleSection,
    ],
  },
  ira: {
    title: 'IRA Account',
    sections: [
      {
        title: 'Account Info',
        fields: [
          { name: 'name', label: 'Account Name', type: 'text', required: true },
          {
            name: 'account_type',
            label: 'Account Type',
            type: 'select',
            options: [
              { value: 'traditional', label: 'Traditional IRA' },
              { value: 'roth', label: 'Roth IRA' },
            ],
          },
          { name: 'initial_balance', label: 'Initial Balance', type: 'currency' },
          { name: 'expected_annual_return', label: 'Expected Return %', type: 'percent' },
        ],
      },
      {
        title: 'Options',
        fields: [
          { name: 'is_backdoor', label: 'Backdoor Roth Strategy', type: 'switch' },
        ],
      },
      scheduleSection,
    ],
  },
  five_twenty_nine: {
    title: '529 Education Plan',
    sections: [
      {
        title: 'Plan Info',
        fields: [
          { name: 'name', label: 'Plan Name', type: 'text', required: true },
          { name: 'beneficiary', label: 'Beneficiary Name', type: 'text' },
          { name: 'initial_balance', label: 'Initial Balance', type: 'currency' },
          { name: 'expected_annual_return', label: 'Expected Return %', type: 'percent' },
        ],
      },
      {
        title: 'Limits',
        fields: [
          { name: 'max_annual_contribution', label: 'Max Annual Contribution', type: 'currency' },
          { name: 'target_college_year', label: 'Target College Year', type: 'number' },
        ],
      },
      scheduleSection,
    ],
  },
  real_estate: {
    title: 'Real Estate Property',
    sections: [
      {
        title: 'Property Info',
        fields: [
          { name: 'property_name', label: 'Property Name', type: 'text', required: true },
          { name: 'purchase_price', label: 'Purchase Price', type: 'currency', required: true },
        ],
      },
      {
        title: 'Loan',
        fields: [
          { name: 'loan_obj.down_payment_pct', label: 'Down Payment %', type: 'percent' },
          { name: 'loan_obj.interest_rate_pct', label: 'Interest Rate %', type: 'percent' },
          { name: 'loan_obj.loan_term', label: 'Loan Term (Years)', type: 'number' },
          { name: 'closing_cost', label: 'Closing Cost', type: 'currency' },
        ],
      },
      {
        title: 'Income',
        fields: [
          { name: 'income_obj.monthly_rent', label: 'Monthly Rent', type: 'currency' },
          { name: 'income_obj.annual_rent_increase', label: 'Annual Rent Increase %', type: 'percent' },
          { name: 'income_obj.vacancy_rate_pct', label: 'Vacancy Rate %', type: 'percent' },
          { name: 'income_obj.management_fee', label: 'Management Fee %', type: 'percent' },
        ],
      },
      {
        title: 'Expenses',
        fields: [
          { name: 'annual_property_tax', label: 'Annual Property Tax', type: 'currency' },
          { name: 'annual_total_insurance', label: 'Annual Insurance', type: 'currency' },
          { name: 'annual_maintenance', label: 'Annual Maintenance', type: 'currency' },
          { name: 'annual_hoa', label: 'Annual HOA', type: 'currency' },
        ],
      },
      {
        title: 'Appreciation',
        fields: [
          { name: 'value_appreciation_per_year_pct', label: 'Annual Appreciation %', type: 'percent' },
          { name: 'holding_length', label: 'Holding Period (Months)', type: 'number' },
          { name: 'cost_to_sell_pct', label: 'Cost to Sell %', type: 'percent' },
        ],
      },
      scheduleSection,
    ],
  },
  mortgage: {
    title: 'Mortgage',
    sections: [
      {
        title: 'Loan Info',
        fields: [
          { name: 'name', label: 'Mortgage Name', type: 'text', required: true },
          { name: 'original_principal', label: 'Loan Amount', type: 'currency', required: true },
          { name: 'interest_rate_pct', label: 'Interest Rate %', type: 'percent' },
          { name: 'term_years', label: 'Loan Term (Years)', type: 'number' },
        ],
      },
      {
        title: 'Property',
        fields: [
          { name: 'property_value', label: 'Property Value', type: 'currency' },
          { name: 'is_primary_residence', label: 'Primary Residence', type: 'switch' },
        ],
      },
      {
        title: 'Extra Payments',
        fields: [
          { name: 'extra_monthly_payment', label: 'Extra Monthly Payment', type: 'currency' },
        ],
      },
      scheduleSection,
    ],
  },
  debt: {
    title: 'Debt / Loan',
    sections: [
      {
        title: 'Loan Info',
        fields: [
          { name: 'name', label: 'Debt Name', type: 'text', required: true },
          {
            name: 'debt_type',
            label: 'Debt Type',
            type: 'select',
            options: [
              { value: 'student_loan', label: 'Student Loan' },
              { value: 'car_loan', label: 'Car Loan' },
              { value: 'personal_loan', label: 'Personal Loan' },
              { value: 'credit_card', label: 'Credit Card' },
            ],
          },
          { name: 'current_balance', label: 'Current Balance', type: 'currency', required: true },
          { name: 'original_principal', label: 'Original Amount', type: 'currency' },
        ],
      },
      {
        title: 'Interest & Payments',
        fields: [
          { name: 'interest_rate_pct', label: 'Interest Rate %', type: 'percent', required: true },
          { name: 'minimum_payment', label: 'Minimum Payment', type: 'currency' },
          { name: 'loan_term_months', label: 'Loan Term (Months)', type: 'number' },
          { name: 'extra_payment', label: 'Extra Monthly Payment', type: 'currency' },
        ],
      },
      {
        title: 'Tax Options',
        fields: [
          { name: 'is_tax_deductible', label: 'Tax Deductible Interest', type: 'switch' },
        ],
      },
      scheduleSection,
    ],
  },
  expense: {
    title: 'Expense',
    sections: [
      {
        title: 'Expense Info',
        fields: [
          { name: 'name', label: 'Expense Name', type: 'text', required: true },
          {
            name: 'expense_type',
            label: 'Expense Type',
            type: 'select',
            options: [
              { value: 'fixed', label: 'Fixed Monthly' },
              { value: 'variable', label: 'Variable Monthly' },
              { value: 'annual', label: 'Annual' },
              { value: 'seasonal', label: 'Seasonal' },
            ],
          },
          {
            name: 'category',
            label: 'Category',
            type: 'select',
            options: [
              { value: 'childcare', label: 'Childcare' },
              { value: 'education', label: 'Education' },
              { value: 'utilities', label: 'Utilities' },
              { value: 'subscription', label: 'Subscription' },
              { value: 'healthcare', label: 'Healthcare' },
              { value: 'transportation', label: 'Transportation' },
              { value: 'food', label: 'Food & Dining' },
              { value: 'entertainment', label: 'Entertainment' },
              { value: 'other', label: 'Other' },
            ],
          },
        ],
      },
      {
        title: 'Amount',
        fields: [
          { name: 'monthly_amount', label: 'Monthly Amount', type: 'currency' },
          { name: 'annual_amount', label: 'Annual Amount', type: 'currency' },
          { name: 'annual_increase_pct', label: 'Annual Increase %', type: 'percent' },
        ],
      },
      {
        title: 'Tax Options',
        fields: [
          { name: 'is_tax_deductible', label: 'Tax Deductible/Credit', type: 'switch' },
          {
            name: 'tax_deduction_type',
            label: 'Tax Benefit Type',
            type: 'select',
            options: [
              { value: 'none', label: 'None' },
              { value: 'childcare_credit', label: 'Childcare Credit' },
              { value: 'medical', label: 'Medical Deduction' },
              { value: 'education', label: 'Education Credit' },
            ],
          },
        ],
      },
      scheduleSection,
    ],
  },
};

// Helper to get nested value
const getNestedValue = (obj, path) => {
  return path.split('.').reduce((o, p) => (o ? o[p] : undefined), obj);
};

// Helper to set nested value
const setNestedValue = (obj, path, value) => {
  const parts = path.split('.');
  const last = parts.pop();
  const target = parts.reduce((o, p) => {
    if (!o[p]) o[p] = {};
    return o[p];
  }, obj);
  target[last] = value;
  return obj;
};

function NodeConfigDrawer({ open, node, onUpdate, onDelete, onClose }) {
  const [form] = Form.useForm();
  const moduleType = node?.data?.moduleType;
  const formConfig = formConfigs[moduleType];

  useEffect(() => {
    if (node && formConfig) {
      const initialValues = {};
      formConfig.sections.forEach((section) => {
        section.fields.forEach((field) => {
          const value = getNestedValue(node.data.config, field.name);
          if (value !== undefined) {
            initialValues[field.name] = value;
          }
        });
      });
      form.setFieldsValue(initialValues);
    }
  }, [node, form, formConfig]);

  const handleSave = () => {
    form.validateFields().then((values) => {
      const newConfig = { ...node.data.config };
      Object.entries(values).forEach(([key, value]) => {
        if (key.includes('.')) {
          setNestedValue(newConfig, key, value);
        } else {
          newConfig[key] = value;
        }
      });
      // Handle name mapping for real_estate
      if (moduleType === 'real_estate' && values.property_name) {
        newConfig.name = values.property_name;
      }
      onUpdate(node.id, newConfig);
    });
  };

  const renderField = (field) => {
    const commonProps = {
      name: field.name,
      label: field.label,
      rules: field.required ? [{ required: true, message: `${field.label} is required` }] : [],
    };

    switch (field.type) {
      case 'text':
        return (
          <Form.Item key={field.name} {...commonProps}>
            <Input />
          </Form.Item>
        );
      case 'currency':
        return (
          <Form.Item key={field.name} {...commonProps}>
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              precision={2}
              formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(value) => value.replace(/\$\s?|(,*)/g, '')}
            />
          </Form.Item>
        );
      case 'percent':
        return (
          <Form.Item key={field.name} {...commonProps}>
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              max={100}
              precision={2}
              formatter={(value) => `${value}%`}
              parser={(value) => value.replace('%', '')}
            />
          </Form.Item>
        );
      case 'number':
        return (
          <Form.Item key={field.name} {...commonProps}>
            <InputNumber style={{ width: '100%' }} min={0} />
          </Form.Item>
        );
      case 'select':
        return (
          <Form.Item key={field.name} {...commonProps}>
            <Select>
              {field.options.map((opt) => (
                <Option key={opt.value} value={opt.value}>
                  {opt.label}
                </Option>
              ))}
            </Select>
          </Form.Item>
        );
      case 'switch':
        return (
          <Form.Item key={field.name} {...commonProps} valuePropName="checked">
            <Switch />
          </Form.Item>
        );
      case 'year':
        return (
          <Form.Item key={field.name} {...commonProps}>
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              max={2100}
              placeholder="YYYY (0 = use simulation start)"
            />
          </Form.Item>
        );
      case 'month':
        return (
          <Form.Item key={field.name} {...commonProps}>
            <Select placeholder="Select month" allowClear>
              <Option value={1}>January</Option>
              <Option value={2}>February</Option>
              <Option value={3}>March</Option>
              <Option value={4}>April</Option>
              <Option value={5}>May</Option>
              <Option value={6}>June</Option>
              <Option value={7}>July</Option>
              <Option value={8}>August</Option>
              <Option value={9}>September</Option>
              <Option value={10}>October</Option>
              <Option value={11}>November</Option>
              <Option value={12}>December</Option>
            </Select>
          </Form.Item>
        );
      default:
        return null;
    }
  };

  if (!formConfig) {
    return (
      <Drawer title="Configure Node" open={open} onClose={onClose} width={400}>
        <Text type="secondary">Unknown node type: {moduleType}</Text>
      </Drawer>
    );
  }

  return (
    <Drawer
      title={formConfig.title}
      open={open}
      onClose={onClose}
      width={400}
      footer={
        <Space style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Popconfirm
            title="Delete this node?"
            onConfirm={() => onDelete(node.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button danger icon={<DeleteOutlined />}>
              Delete
            </Button>
          </Popconfirm>
          <Space>
            <Button onClick={onClose}>Cancel</Button>
            <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
              Save
            </Button>
          </Space>
        </Space>
      }
    >
      {/* Show current simulated balance if available */}
      {node?.data?.simulatedBalance !== undefined && (
        <Card
          size="small"
          style={{ marginBottom: 16 }}
          bodyStyle={{ padding: '12px 16px' }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>Current Simulated Value</Text>
              <div style={{ fontSize: 20, fontWeight: 600, color: node.data.simulatedBalance >= 0 ? '#52c41a' : '#f5222d' }}>
                <DollarOutlined style={{ marginRight: 4 }} />
                {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(Math.abs(node.data.simulatedBalance))}
                {node.data.simulatedBalance < 0 && ' (owed)'}
              </div>
            </div>
            {node?.data?.isInactive && (
              <Tag color="orange">Inactive</Tag>
            )}
          </div>
        </Card>
      )}

      <Form form={form} layout="vertical" size="small">
        <Collapse
          defaultActiveKey={formConfig.sections.map((_, i) => i.toString())}
          ghost
          expandIconPosition="end"
        >
          {formConfig.sections.map((section, index) => (
            <Panel header={<Text strong>{section.title}</Text>} key={index.toString()}>
              {section.fields.map(renderField)}
            </Panel>
          ))}
        </Collapse>
      </Form>
    </Drawer>
  );
}

export default NodeConfigDrawer;
