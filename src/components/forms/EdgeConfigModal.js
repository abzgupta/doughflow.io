import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Radio,
  Switch,
  Space,
  Typography,
  Divider,
  Button,
  Popconfirm,
} from 'antd';
import { DeleteOutlined } from '@ant-design/icons';

const { Text } = Typography;
const { Option } = Select;

function EdgeConfigModal({ open, edge, onSave, onDelete, onCancel }) {
  const [form] = Form.useForm();
  const [flowType, setFlowType] = useState('remainder');
  const [hasCondition, setHasCondition] = useState(false);

  // Reset form when edge changes
  useEffect(() => {
    if (edge) {
      const data = edge.data || {};
      setFlowType(data.flowType || 'remainder');
      setHasCondition(!!data.condition);
      form.setFieldsValue({
        flowType: data.flowType || 'remainder',
        amount: data.amount || 0,
        frequency: data.frequency || 'monthly',
        priority: data.priority || 0,
        conditionType: data.condition?.type || 'threshold',
        conditionValue: data.condition?.source_balance_min || 0,
      });
    } else {
      form.resetFields();
      setFlowType('remainder');
      setHasCondition(false);
    }
  }, [edge, form]);

  const handleSubmit = () => {
    form.validateFields().then((values) => {
      const edgeConfig = {
        flowType: values.flowType,
        amount: values.flowType === 'remainder' ? 0 : values.amount,
        frequency: values.frequency,
        priority: values.priority || 0,
        condition: hasCondition
          ? {
              type: values.conditionType,
              source_balance_min:
                values.conditionType === 'threshold' ? values.conditionValue : undefined,
              target_balance_max:
                values.conditionType === 'target_max' ? values.conditionValue : undefined,
            }
          : null,
      };

      if (edge?.id) {
        onSave(edge.id, edgeConfig);
      } else {
        onSave(edgeConfig);
      }
    });
  };

  return (
    <Modal
      title={edge?.id ? 'Edit Money Flow' : 'Configure Money Flow'}
      open={open}
      onOk={handleSubmit}
      onCancel={onCancel}
      width={480}
      footer={[
        edge?.id && onDelete && (
          <Popconfirm
            key="delete"
            title="Delete this connection?"
            onConfirm={onDelete}
            okText="Yes"
            cancelText="No"
          >
            <Button danger icon={<DeleteOutlined />}>
              Delete
            </Button>
          </Popconfirm>
        ),
        <Button key="cancel" onClick={onCancel}>
          Cancel
        </Button>,
        <Button key="save" type="primary" onClick={handleSubmit}>
          Save
        </Button>,
      ].filter(Boolean)}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          flowType: 'remainder',
          amount: 0,
          frequency: 'monthly',
          priority: 0,
          conditionType: 'threshold',
          conditionValue: 0,
        }}
      >
        <Form.Item
          name="flowType"
          label="Flow Type"
          tooltip="How to calculate the transfer amount"
        >
          <Radio.Group onChange={(e) => setFlowType(e.target.value)}>
            <Space direction="vertical">
              <Radio value="remainder">
                <Text strong>Remainder</Text>
                <Text type="secondary" style={{ marginLeft: 8 }}>
                  Transfer all available funds
                </Text>
              </Radio>
              <Radio value="fixed">
                <Text strong>Fixed Amount</Text>
                <Text type="secondary" style={{ marginLeft: 8 }}>
                  Transfer a specific dollar amount
                </Text>
              </Radio>
              <Radio value="percentage">
                <Text strong>Percentage</Text>
                <Text type="secondary" style={{ marginLeft: 8 }}>
                  Transfer a percentage of available funds
                </Text>
              </Radio>
            </Space>
          </Radio.Group>
        </Form.Item>

        {flowType !== 'remainder' && (
          <Form.Item
            name="amount"
            label={flowType === 'fixed' ? 'Amount ($)' : 'Percentage (%)'}
            rules={[{ required: true, message: 'Please enter an amount' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              max={flowType === 'percentage' ? 100 : undefined}
              precision={flowType === 'fixed' ? 2 : 0}
              prefix={flowType === 'fixed' ? '$' : undefined}
              suffix={flowType === 'percentage' ? '%' : undefined}
              placeholder={flowType === 'fixed' ? '1000.00' : '50'}
            />
          </Form.Item>
        )}

        <Form.Item
          name="frequency"
          label="Frequency"
          tooltip="How often this transfer occurs"
        >
          <Select>
            <Option value="monthly">Monthly</Option>
            <Option value="quarterly">Quarterly</Option>
            <Option value="annually">Annually</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="priority"
          label="Priority"
          tooltip="Lower numbers execute first when multiple outflows exist"
        >
          <InputNumber
            style={{ width: '100%' }}
            min={0}
            max={99}
            placeholder="0"
          />
        </Form.Item>

        <Divider style={{ margin: '16px 0' }} />

        <div style={{ marginBottom: 16 }}>
          <Switch
            checked={hasCondition}
            onChange={setHasCondition}
            style={{ marginRight: 8 }}
          />
          <Text>Add Condition</Text>
          <Text type="secondary" style={{ display: 'block', marginLeft: 46, fontSize: 12 }}>
            Only transfer when condition is met
          </Text>
        </div>

        {hasCondition && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Form.Item name="conditionType" label="Condition Type">
              <Select>
                <Option value="threshold">Source Balance Minimum</Option>
                <Option value="target_max">Target Balance Maximum</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="conditionValue"
              label="Threshold Amount ($)"
              rules={[{ required: hasCondition, message: 'Please enter a threshold' }]}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                precision={2}
                prefix="$"
                placeholder="10000.00"
              />
            </Form.Item>
          </Space>
        )}
      </Form>
    </Modal>
  );
}

export default EdgeConfigModal;
