import React, { useState } from "react";
import { Sankey } from "react-vis";
import { Button, Modal, Form, Input } from "antd";

const BudgetSankey = () => {
  const [modalVisible, setModalVisible] = useState(false);
  const [cashflowData, setCashflowData] = useState({ nodes: [], links: [] });

  const parseCashflowData = (data) => {
    const lines = data.split("\n").filter((line) => line.trim() !== "");
    const nodes = [];
    const nodeMap = new Map();
    const links = [];

    lines.forEach((line) => {
      const [source, target] = line.split("]");
      const [sourceLabel, sourceValue] = source.split("[");
      const targetLabel = target.trim();

      if (!nodeMap.has(sourceLabel.trim())) {
        nodeMap.set(sourceLabel.trim(), nodes.length);
        nodes.push({ name: sourceLabel.trim() + ":" + sourceValue });
      }

      if (!nodeMap.has(targetLabel)) {
        nodeMap.set(targetLabel, nodes.length);
        nodes.push({ name: targetLabel + ":" + sourceValue });
      }

      const sourceIndex = nodeMap.get(sourceLabel.trim());
      const targetIndex = nodeMap.get(targetLabel);

      links.push({
        source: sourceIndex,
        target: targetIndex,
        value: parseFloat(sourceValue),
      });
    });

    return { nodes, links };
  };

  const handleFormSubmit = (values) => {
    const cashflowData = values.cashflowData;
    const parsedData = parseCashflowData(cashflowData);
    console.log(parsedData);
    setCashflowData(parsedData);
    setModalVisible(false);
  };

  return (
    <div>
      <Button type="primary" onClick={() => setModalVisible(true)}>
        New Cashflow
      </Button>
      <Modal
        title="New Cashflow"
        visible={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
      >
        <Form onFinish={handleFormSubmit}>
          <Form.Item
            name="cashflowData"
            label="Cashflow Data"
            rules={[{ required: true, message: "Please enter cashflow data" }]}
          >
            <Input.TextArea rows={6} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">
              Submit
            </Button>
          </Form.Item>
        </Form>
      </Modal>
      {cashflowData.nodes.length > 0 && (
        <Sankey
          nodes={cashflowData.nodes}
          links={cashflowData.links}
          width={600}
          height={400}
          nodeWidth={15}
          nodePadding={10}
          labelFormatter={(node) => `${node.name}`}
          style={{
            labels: {
              fontSize: "14px",
              fontWeight: "bold",
              fill: "#333",
            },
            links: {
              opacity: 0.3,
            },
            rects: {
              fill: "#1890ff",
              stroke: "#1890ff",
            },
          }}
        />
      )}
    </div>
  );
};

export default BudgetSankey;
