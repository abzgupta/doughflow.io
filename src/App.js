import React, { useState } from 'react';
import { Layout, Menu, Button, Space, Dropdown, Modal, Upload, message, Typography } from 'antd';
import {
  NodeIndexOutlined,
  SaveOutlined,
  FolderOpenOutlined,
  FileAddOutlined,
  UploadOutlined,
} from '@ant-design/icons';

import { GraphProvider } from './context/GraphContext';
import FlowCanvas from './components/flow/FlowCanvas';
import SimulationPanel from './components/panels/SimulationPanel';
import TaxSummaryPanel from './components/panels/TaxSummaryPanel';
import UserProfilePanel from './components/panels/UserProfilePanel';
import { useGraphState } from './hooks/useGraphState';
import { useGraph } from './context/GraphContext';

// Legacy imports for real estate mode
import LegacyApp from './LegacyApp';

import 'reactflow/dist/style.css';
import './App.css';

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

// Main app content (needs to be inside GraphProvider)
function AppContent() {
  const graph = useGraph();
  const { saveGraph, loadGraphFromFile } = useGraphState();

  const [rightPanel, setRightPanel] = useState('simulation'); // 'simulation' | 'tax' | 'profile'
  const [loadModalOpen, setLoadModalOpen] = useState(false);

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
          <NodeIndexOutlined style={{ fontSize: 24, color: '#1890ff' }} />
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
