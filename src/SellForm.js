import React, { useState } from "react";
import {
  Modal,
  Form,
  InputNumber,
  Switch,
  Button,
  Input,
  Select,
  Row,
  Col,
} from "antd";
import { FormItemInputContext } from "antd/es/form/context";

const { Option } = Select;

const SellForm = ({ visible, onCreate, onCancel, currentMonth }) => {
  const [form] = Form.useForm();
  const [useLoan, setUseLoan] = useState(true);
  const [knowSellPrice, setKnowSellPrice] = useState(false);
  const [needRepairs, setNeedRepairs] = useState(true);

  // The initial form values are based on the provided object
  const initialValues = {
    property_name: "property_A",
    purchase_price: 100000,
    use_loan: true,
    loan_obj: {
      down_payment_pct: 20,
      interest_rate_pct: 4.5,
      loan_term: 30,
    },
    closing_cost: 3000,
    need_repairs: true,
    repairs_obj: {
      repair_cost: 10000,
      value_after_repair: 150000,
    },
    income_obj: {
      monthly_rent: 1000,
      annual_rent_increase: 3,
      other_monthly_income: 0,
      other_monthly_income_increase: 0,
      vacancy_rate_pct: 5,
      management_fee: 8,
    },
    annual_property_tax: 1500,
    annual_property_tax_increase_pct: 3,
    annual_total_insurance: 800,
    annual_total_insurance_increase_pct: 3,
    annual_hoa: 100,
    annual_hoa_increase_pct: 3,
    annual_maintenance: 1000,
    annual_maintenance_increase_pct: 3,
    annual_other_costs: 200,
    annual_other_costs_increase_pct: 3,
    know_sell_price: false,
    value_appreciation_per_year_pct: 3,
    cost_to_sell_pct: 8,
    holding_length: 40,
  };

  return (
    <Modal
      visible={visible}
      title="Rental Property Calculator"
      okText="Calculate"
      cancelText="Clear"
      onCancel={onCancel}
      footer={[
        <Button key="clear" onClick={onCancel}>
          Clear
        </Button>,
        <Button
          key="submit"
          type="primary"
          onClick={() => {
            form
              .validateFields()
              .then((values) => {
                const valuesWithMonthOffset = {
                  ...values,
                  month_offset: currentMonth-1,
                  holding_length: values.holding_length * 12, // Convert years to months
                  is_sold:false
                };
                form.resetFields();
                onCreate(valuesWithMonthOffset);
              })
              .catch((info) => {
                console.log("Validate Failed:", info);
              });
          }}
        >
          Calculate
        </Button>,
      ]}
    >
      <Form
        form={form}
        layout="vertical"
        name="property_form"
        initialValues={initialValues}
      >
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="property_name" label="Property Name">
              <Input placeholder="property name" />
            </Form.Item>
            <h3>Purchase</h3>
            <Form.Item name="purchase_price" label="Purchase Price">
              <InputNumber prefix="$" style={{ width: "100%" }} />
            </Form.Item>

            <Form.Item label="Use Loan?" valuePropName="checked">
              <Switch onChange={setUseLoan} />
            </Form.Item>

            {useLoan && (
              <>
                <Form.Item
                  name={["loan_obj", "down_payment_pct"]}
                  label="Down Payment"
                >
                  <InputNumber
                    min={0}
                    max={100}
                    formatter={(value) => `${value}%`}
                    parser={(value) => value.replace("%", "")}
                    style={{ width: "100%" }}
                  />
                </Form.Item>
                <Form.Item
                  name={["loan_obj", "interest_rate_pct"]}
                  label="Interest Rate"
                >
                  <InputNumber
                    min={0}
                    formatter={(value) => `${value}%`}
                    parser={(value) => value.replace("%", "")}
                    style={{ width: "100%" }}
                  />
                </Form.Item>
                <Form.Item name={["loan_obj", "loan_term"]} label="Loan Term">
                  <InputNumber
                    min={0}
                    addonAfter="years"
                    style={{ width: "100%" }}
                  />
                </Form.Item>
              </>
            )}

            <Form.Item name="closing_cost" label="Closing Cost">
              <InputNumber prefix="$" style={{ width: "100%" }} />
            </Form.Item>

            <Form.Item label="Need Repairs?" valuePropName="checked">
              <Switch onChange={setNeedRepairs} />
            </Form.Item>

            {needRepairs && (
              <>
                <Form.Item
                  name={["repairs_obj", "repair_cost"]}
                  label="Repair Cost"
                >
                  <InputNumber prefix="$" style={{ width: "100%" }} />
                </Form.Item>
                <Form.Item
                  name={["repairs_obj", "value_after_repair"]}
                  label="Value After Repair"
                >
                  <InputNumber prefix="$" style={{ width: "100%" }} />
                </Form.Item>
              </>
            )}
          </Col>

          <Col span={12}>
            <h3>Income</h3>
            <Form.Item
              name={["income_obj", "monthly_rent"]}
              label="Monthly Rent"
            >
              <InputNumber prefix="$" style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              name={["income_obj", "annual_rent_increase"]}
              label="Annual Increase"
            >
              <InputNumber
                min={0}
                formatter={(value) => `${value}%`}
                parser={(value) => value.replace("%", "")}
                style={{ width: "100%" }}
              />
            </Form.Item>
            <Form.Item
              name={["income_obj", "other_monthly_income"]}
              label="Other Monthly Income"
            >
              <InputNumber prefix="$" style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              name={["income_obj", "other_monthly_income_increase"]}
              label="Annual Increase"
            >
              <InputNumber
                min={0}
                formatter={(value) => `${value}%`}
                parser={(value) => value.replace("%", "")}
                style={{ width: "100%" }}
              />
            </Form.Item>
            <Form.Item
              name={["income_obj", "vacancy_rate_pct"]}
              label="Vacancy Rate"
            >
              <InputNumber
                min={0}
                formatter={(value) => `${value}%`}
                parser={(value) => value.replace("%", "")}
                style={{ width: "100%" }}
              />
            </Form.Item>
            <Form.Item
              name={["income_obj", "management_fee"]}
              label="Management Fee"
            >
              <InputNumber
                min={0}
                formatter={(value) => `${value}%`}
                parser={(value) => value.replace("%", "")}
                style={{ width: "100%" }}
              />
            </Form.Item>
          </Col>
        </Row>

        <h3>Recurring Operating Expenses</h3>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Property Tax">
              <Row gutter={8}>
                <Col span={12}>
                  <Form.Item name="annual_property_tax">
                    <InputNumber prefix="$" style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="annual_property_tax_increase_pct"
                    label="Annual Increase"
                  >
                    <InputNumber
                      min={0}
                      formatter={(value) => `${value}%`}
                      parser={(value) => value.replace("%", "")}
                      style={{ width: "100%" }}
                    />
                  </Form.Item>
                </Col>
              </Row>
            </Form.Item>

            <Form.Item label="Total Insurance">
              <Row gutter={8}>
                <Col span={12}>
                  <Form.Item name="annual_total_insurance">
                    <InputNumber prefix="$" style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="annual_total_insurance_increase_pct"
                    label="Annual Increase"
                  >
                    <InputNumber
                      min={0}
                      formatter={(value) => `${value}%`}
                      parser={(value) => value.replace("%", "")}
                      style={{ width: "100%" }}
                    />
                  </Form.Item>
                </Col>
              </Row>
            </Form.Item>

            <Form.Item label="HOA Fee">
              <Row gutter={8}>
                <Col span={12}>
                  <Form.Item name="annual_hoa">
                    <InputNumber prefix="$" style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="annual_hoa_increase_pct"
                    label="Annual Increase"
                  >
                    <InputNumber
                      min={0}
                      formatter={(value) => `${value}%`}
                      parser={(value) => value.replace("%", "")}
                      style={{ width: "100%" }}
                    />
                  </Form.Item>
                </Col>
              </Row>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Maintenance">
              <Row gutter={8}>
                <Col span={12}>
                  <Form.Item name="annual_maintenance">
                    <InputNumber prefix="$" style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="annual_maintenance_increase_pct"
                    label="Annual Increase"
                  >
                    <InputNumber
                      min={0}
                      formatter={(value) => `${value}%`}
                      parser={(value) => value.replace("%", "")}
                      style={{ width: "100%" }}
                    />
                  </Form.Item>
                </Col>
              </Row>
            </Form.Item>

            <Form.Item label="Other Costs">
              <Row gutter={8}>
                <Col span={12}>
                  <Form.Item name="annual_other_costs">
                    <InputNumber prefix="$" style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="annual_other_costs_increase_pct"
                    label="Annual Increase"
                  >
                    <InputNumber
                      min={0}
                      formatter={(value) => `${value}%`}
                      parser={(value) => value.replace("%", "")}
                      style={{ width: "100%" }}
                    />
                  </Form.Item>
                </Col>
              </Row>
            </Form.Item>
          </Col>
        </Row>

        <h3>Sell</h3>
        <Form.Item label="Do You Know the Sell Price?" valuePropName="checked">
          <Switch onChange={setKnowSellPrice} />
        </Form.Item>

        {knowSellPrice && (
          <Form.Item name="sell_price" label="Sell Price">
            <InputNumber prefix="$" style={{ width: "100%" }} />
          </Form.Item>
        )}

        {!knowSellPrice && (
          <>
            <Form.Item
              name="value_appreciation_per_year_pct"
              label="Value Appreciation"
            >
              <InputNumber
                min={0}
                formatter={(value) => `${value}%`}
                parser={(value) => value.replace("%", "")}
                addonAfter="per year"
                style={{ width: "100%" }}
              />
            </Form.Item>
            <Form.Item name="holding_length" label="Holding Length">
              <InputNumber
                min={0}
                addonAfter="years"
                style={{ width: "100%" }}
              />
            </Form.Item>
          </>
        )}

        <Form.Item name="cost_to_sell_pct" label="Cost to Sell">
          <InputNumber
            min={0}
            formatter={(value) => `${value}%`}
            parser={(value) => value.replace("%", "")}
            style={{ width: "100%" }}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default SellForm;
