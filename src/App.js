import React, { useEffect, useRef, useState } from 'react';
import { Layout, Menu, Button, Space, Dropdown, Modal, Upload, message, Typography, Alert } from 'antd';
import {
  SaveOutlined,
  FolderOpenOutlined,
  FileAddOutlined,
  UploadOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';

import { GraphProvider } from './context/GraphContext';
import FlowCanvas from './components/flow/FlowCanvas';
import SimulationPanel from './components/panels/SimulationPanel';
import TaxSummaryPanel from './components/panels/TaxSummaryPanel';
import UserProfilePanel from './components/panels/UserProfilePanel';
import { useGraphState } from './hooks/useGraphState';
import { useGraph } from './context/GraphContext';
import sampleGraph from './examples/sampleGraph.json';
import Disclaimer from './Disclaimer';

// Legacy imports for real estate mode
import LegacyApp from './LegacyApp';

import 'reactflow/dist/style.css';
import './App.css';

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

// Main app content (needs to be inside GraphProvider)
function AppContent() {
  const graph = useGraph();
  const { saveGraph, loadGraphFromFile, runSimulation } = useGraphState();

  const [rightPanel, setRightPanel] = useState('simulation'); // 'simulation' | 'tax' | 'profile'
  const [loadModalOpen, setLoadModalOpen] = useState(false);
  const [disclaimerOpen, setDisclaimerOpen] = useState(false);

  // Bumping runToken runs the simulation once after the next render, so it
  // sees freshly loaded nodes. The ref keeps StrictMode from running it twice.
  const [runToken, setRunToken] = useState(1); // 1 = run the example on first load
  const lastRunTokenRef = useRef(0);

  useEffect(() => {
    if (lastRunTokenRef.current === runToken) return;
    lastRunTokenRef.current = runToken;
    runSimulation().then((result) => {
      if (!result) {
        message.error("Couldn't run the simulation. Is the backend running? See the README.");
      }
    });
  }, [runToken, runSimulation]);

  const loadExample = () => {
    graph.loadGraph(sampleGraph);
    setRunToken((t) => t + 1);
  };

  // Handle save - triggers file download
  const handleSave = () => {
    saveGraph();
    message.success('Graph downloaded as JSON file');
  };

  // Handle file upload for loading
  const handleFileUpload = async (file) => {
    try {
      await loadGraphFromFile(file);
      message.success('Graph loaded successfully');
      setLoadModalOpen(false);
    } catch (err) {
      message.error(err.message || 'Failed to load graph');
    }
    return false; // Prevent default upload behavior
  };

  // File menu items
  const fileMenuItems = [
    {
      key: 'new',
      icon: <FileAddOutlined />,
      label: 'New Graph',
      onClick: () => {
        if (graph.isDirty) {
          Modal.confirm({
            title: 'Unsaved Changes',
            content: 'You have unsaved changes. Are you sure you want to create a new graph?',
            onOk: () => graph.clearGraph(),
          });
        } else {
          graph.clearGraph();
        }
      },
    },
    {
      key: 'example',
      icon: <ExperimentOutlined />,
      label: 'Load Example',
      onClick: () => {
        if (graph.isDirty) {
          Modal.confirm({
            title: 'Unsaved Changes',
            content: 'You have unsaved changes. Replace them with the example graph?',
            onOk: loadExample,
          });
        } else {
          loadExample();
        }
      },
    },
    {
      key: 'save',
      icon: <SaveOutlined />,
      label: 'Save Graph (Download)',
      onClick: handleSave,
    },
    {
      key: 'load',
      icon: <FolderOpenOutlined />,
      label: 'Load Graph (Upload)',
      onClick: () => setLoadModalOpen(true),
    },
  ];

  return (
    <Layout style={{ height: '100vh' }}>
      {/* Header */}
      <Header
        style={{
          background: '#fff',
          padding: '0 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #f0f0f0',
          height: 48,
        }}
      >
        <Space>
          <img src={`${process.env.PUBLIC_URL}/favicon.svg`} alt="" width={28} height={28} style={{ display: 'block' }} />
          <Title level={4} style={{ margin: 0 }}>
            DoughFlow
          </Title>
          <Text type="secondary">Financial Flow Simulator</Text>
        </Space>

        <Space>
          <Dropdown menu={{ items: fileMenuItems }} placement="bottomRight">
            <Button icon={<FolderOpenOutlined />}>File</Button>
          </Dropdown>

          <Button
            icon={<SaveOutlined />}
            onClick={handleSave}
            disabled={!graph.isDirty}
          >
            Save
          </Button>
        </Space>
      </Header>

      {/* Always-visible disclaimer */}
      <Alert
        type="warning"
        banner
        showIcon
        message={
          <span>
            Educational tool only, not financial or tax advice. Numbers may be wrong. Consult a
            financial advisor and tax professional before making decisions.{' '}
            <Button type="link" size="small" style={{ padding: 0 }} onClick={() => setDisclaimerOpen(true)}>
              Full disclaimer
            </Button>
          </span>
        }
      />

      <Layout>
        {/* Main Content - Flow Canvas */}
        <Content style={{ position: 'relative' }}>
          <FlowCanvas />
        </Content>

        {/* Right Sidebar - Panels */}
        <Sider
          width={320}
          theme="light"
          style={{
            borderLeft: '1px solid #f0f0f0',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Panel Tabs */}
          <Menu
            mode="horizontal"
            selectedKeys={[rightPanel]}
            onClick={(e) => setRightPanel(e.key)}
            style={{ borderBottom: '1px solid #f0f0f0' }}
          >
            <Menu.Item key="simulation">Simulate</Menu.Item>
            <Menu.Item key="tax">Tax</Menu.Item>
            <Menu.Item key="profile">Profile</Menu.Item>
          </Menu>

          {/* Panel Content */}
          <div style={{ flex: 1, overflow: 'hidden' }}>
            {rightPanel === 'simulation' && <SimulationPanel />}
            {rightPanel === 'tax' && <TaxSummaryPanel />}
            {rightPanel === 'profile' && <UserProfilePanel />}
          </div>
        </Sider>
      </Layout>

      {/* Disclaimer Modal */}
      <Modal
        open={disclaimerOpen}
        onCancel={() => setDisclaimerOpen(false)}
        footer={null}
        width={640}
      >
        <Disclaimer />
      </Modal>

      {/* Load Modal */}
      <Modal
        title="Load Graph"
        open={loadModalOpen}
        onCancel={() => setLoadModalOpen(false)}
        footer={null}
      >
        <Upload.Dragger
          accept=".json"
          beforeUpload={handleFileUpload}
          showUploadList={false}
        >
          <p className="ant-upload-drag-icon">
            <UploadOutlined style={{ fontSize: 48, color: '#1890ff' }} />
          </p>
          <p className="ant-upload-text">Click or drag a JSON file to load</p>
          <p className="ant-upload-hint">
            Select a previously saved DoughFlow graph file (.json)
          </p>
        </Upload.Dragger>
      </Modal>
    </Layout>
  );
}

// Main App with mode switch
function App() {
  const [mode, setMode] = useState('flow'); // 'flow' | 'legacy'

  // Check URL for mode
  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('mode') === 'legacy') {
      setMode('legacy');
    }
  }, []);

  if (mode === 'legacy') {
    return <LegacyApp />;
  }

  return (
    <GraphProvider>
      <AppContent />
    </GraphProvider>
  );
}

export default App;
