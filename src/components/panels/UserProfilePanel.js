import React from 'react';
import {
  Card,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Typography,
  Divider,
  Button,
} from 'antd';
import { UserOutlined, SaveOutlined } from '@ant-design/icons';
import { useGraph } from '../../context/GraphContext';

const { Title, Text } = Typography;
const { Option } = Select;

// US States
const US_STATES = [
  { value: 'AL', label: 'Alabama' },
  { value: 'AK', label: 'Alaska' },
  { value: 'AZ', label: 'Arizona' },
  { value: 'AR', label: 'Arkansas' },
  { value: 'CA', label: 'California' },
  { value: 'CO', label: 'Colorado' },
  { value: 'CT', label: 'Connecticut' },
  { value: 'DE', label: 'Delaware' },
  { value: 'FL', label: 'Florida' },
  { value: 'GA', label: 'Georgia' },
  { value: 'HI', label: 'Hawaii' },
  { value: 'ID', label: 'Idaho' },
  { value: 'IL', label: 'Illinois' },
  { value: 'IN', label: 'Indiana' },
  { value: 'IA', label: 'Iowa' },
  { value: 'KS', label: 'Kansas' },
  { value: 'KY', label: 'Kentucky' },
  { value: 'LA', label: 'Louisiana' },
  { value: 'ME', label: 'Maine' },
  { value: 'MD', label: 'Maryland' },
  { value: 'MA', label: 'Massachusetts' },
  { value: 'MI', label: 'Michigan' },
  { value: 'MN', label: 'Minnesota' },
  { value: 'MS', label: 'Mississippi' },
  { value: 'MO', label: 'Missouri' },
  { value: 'MT', label: 'Montana' },
  { value: 'NE', label: 'Nebraska' },
  { value: 'NV', label: 'Nevada' },
  { value: 'NH', label: 'New Hampshire' },
  { value: 'NJ', label: 'New Jersey' },
  { value: 'NM', label: 'New Mexico' },
  { value: 'NY', label: 'New York' },
  { value: 'NC', label: 'North Carolina' },
  { value: 'ND', label: 'North Dakota' },
  { value: 'OH', label: 'Ohio' },
  { value: 'OK', label: 'Oklahoma' },
  { value: 'OR', label: 'Oregon' },
  { value: 'PA', label: 'Pennsylvania' },
  { value: 'RI', label: 'Rhode Island' },
  { value: 'SC', label: 'South Carolina' },
  { value: 'SD', label: 'South Dakota' },
  { value: 'TN', label: 'Tennessee' },
  { value: 'TX', label: 'Texas' },
  { value: 'UT', label: 'Utah' },
  { value: 'VT', label: 'Vermont' },
  { value: 'VA', label: 'Virginia' },
  { value: 'WA', label: 'Washington' },
  { value: 'WV', label: 'West Virginia' },
  { value: 'WI', label: 'Wisconsin' },
  { value: 'WY', label: 'Wyoming' },
];

function UserProfilePanel() {
  const [form] = Form.useForm();
  const graph = useGraph();

  // Initialize form with current values
  React.useEffect(() => {
    form.setFieldsValue(graph.userProfile);
  }, [graph.userProfile, form]);

  const handleValuesChange = (changedValues, allValues) => {
    graph.setUserProfile(allValues);
  };

  return (
    <Card
      title={
        <Space>
          <UserOutlined />
          <span>Profile</span>
        </Space>
      }
      style={{ height: '100%', overflowY: 'auto' }}
      bodyStyle={{ padding: 12 }}
      size="small"
    >
      <Form
        form={form}
        layout="vertical"
        size="small"
        initialValues={graph.userProfile}
        onValuesChange={handleValuesChange}
      >
        <Form.Item name="filing_status" label="Filing Status">
          <Select>
            <Option value="single">Single</Option>
            <Option value="married_jointly">Married Filing Jointly</Option>
            <Option value="married_separately">Married Filing Separately</Option>
            <Option value="head_of_household">Head of Household</Option>
          </Select>
        </Form.Item>

        <Form.Item name="state" label="State">
          <Select
            showSearch
            optionFilterProp="label"
            options={US_STATES}
          />
        </Form.Item>

        <Form.Item name="age" label="Age">
          <InputNumber style={{ width: '100%' }} min={18} max={100} />
        </Form.Item>

        <Form.Item name="dependents" label="Dependents">
          <InputNumber style={{ width: '100%' }} min={0} max={20} />
        </Form.Item>

        <Divider style={{ margin: '12px 0' }} />

        <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 8 }}>
          Simulation Settings
        </Text>

        <Form.Item label="Start Year">
          <InputNumber
            style={{ width: '100%' }}
            value={graph.simulationConfig.start_year}
            min={2020}
            max={2050}
            onChange={(value) => graph.setSimulationConfig({ start_year: value })}
          />
        </Form.Item>

        <Form.Item label="Duration (Months)">
          <InputNumber
            style={{ width: '100%' }}
            value={graph.simulationConfig.duration_months}
            min={12}
            max={600}
            step={12}
            onChange={(value) => graph.setSimulationConfig({ duration_months: value })}
          />
        </Form.Item>
      </Form>
    </Card>
  );
}

export default UserProfilePanel;
