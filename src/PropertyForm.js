import React, { useState, useEffect } from "react";
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
  Divider,
} from "antd";
import { CloseOutlined } from "@ant-design/icons";
import { FormItemInputContext } from "antd/es/form/context";

const { Option } = Select;

const PropertyForm = ({
  visible,
  onCreate,
  onCancel,
  currentMonth,
  initialValues,
  propertyCount,
}) => {
  const [form] = Form.useForm();
  const [useLoan, setUseLoan] = useState(true);
  const [knowSellPrice, setKnowSellPrice] = useState(false);
  const [needRepairs, setNeedRepairs] = useState(true);
  const [noRentMonths, setNoRentMonths] = useState([]);
  const [startMonth, setStartMonth] = useState(null);
  const [endMonth, setEndMonth] = useState(null);

  const initialValues_2 = {
    property_name: `Property_${String.fromCharCode(65 + propertyCount)}`,
    purchase_price: 220000,
    use_loan: true,
    loan_obj: {
      down_payment_pct: 100,
      interest_rate_pct: 4.5,
      loan_term: 30,
    },
    closing_cost: 6000,
    need_repairs: true,
    repairs_obj: {
      repair_cost: 10000,
      value_after_repair: 22000,
    },
    income_obj: {
      monthly_rent: 2000,
      annual_rent_increase: 3,
      other_monthly_income: 0,
      other_monthly_income_increase: 0,
      vacancy_rate_pct: 5,
      management_fee: 8,
    },
    annual_property_tax: 3476,
    annual_property_tax_increase_pct: 3,
    annual_total_insurance: 1000,
    annual_total_insurance_increase_pct: 3,
    annual_hoa: 4032,
    annual_hoa_increase_pct: 3,
    annual_maintenance: 0,
    annual_maintenance_increase_pct: 3,
    annual_other_costs: 200,
    annual_other_costs_increase_pct: 3,
    know_sell_price: false,
    value_appreciation_per_year_pct: 3,
    cost_to_sell_pct: 8,
    holding_length: 50,
  };

  useEffect(() => {
    if (initialValues !== null) {
      form.setFieldsValue(initialValues);
      setUseLoan(initialValues.use_loan);
      setKnowSellPrice(initialValues.know_sell_price);
      setNeedRepairs(initialValues.need_repairs);
      setNoRentMonths(initialValues.no_rent_months || []);
    } else {
      form.setFieldsValue(initialValues_2);
      setUseLoan(initialValues_2.use_loan);
      setKnowSellPrice(initialValues_2.know_sell_price);
      setNeedRepairs(initialValues_2.need_repairs);
      setNoRentMonths([]);
    }
  }, [form, initialValues, visible]);

  const handleAddNoRentMonths = () => {
    if (startMonth !== null && endMonth !== null && endMonth >= startMonth) {
      setNoRentMonths([...noRentMonths, [startMonth, endMonth]]);
      setStartMonth(null);
      setEndMonth(null);
    }
  };

  const handleDeleteNoRentPeriod = (index) => {
    const updatedNoRentMonths = [...noRentMonths];
    updatedNoRentMonths.splice(index, 1);
    setNoRentMonths(updatedNoRentMonths);
  };

  return (
    <Modal
      visible={visible}
      width={700}
      title={initialValues ? "Edit Property" : "Rental Property Calculator"}
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
                  ...initialValues,
                  ...values,
                  month_offset: initialValues
                    ? initialValues["month_offset"]
                    : currentMonth - 1,
                  holding_length: values.holding_length * 12,
                  original_holding_length: values.holding_length * 12,
                  is_sold: false,
                  no_rent_months: noRentMonths,
                  use_loan: useLoan,
                  need_repairs: needRepairs,
                  know_sell_price: knowSellPrice,
                };
                form.resetFields();
                setNoRentMonths([]);
                onCreate(valuesWithMonthOffset);
              })
              .catch((info) => {
                console.log("Validate Failed:", info);
              });
          }}
        >
          {initialValues ? "Update" : "Calculate"}
        </Button>,
      ]}
    >
      <Form form={form} layout="vertical" name="property_form">
        <h3>Property Name</h3>
        <Form.Item name="property_name">
          <Input placeholder="property name" />
        </Form.Item>
        <Divider />
        <Row gutter={16}>
          <Col span={11}>
            <h3>Purchase</h3>
            <Form.Item name="purchase_price" label="Purchase Price">
              <InputNumber prefix="$" style={{ width: "100%" }} />
            </Form.Item>

            <Form.Item label="Use Loan?" valuePropName="checked">
              <Switch checked={useLoan} onChange={setUseLoan} />
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
              <Switch checked={needRepairs} onChange={setNeedRepairs} />
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
          <Col span={2}>
            <Divider type="vertical" style={{ height: "100%" }} />
          </Col>

          <Col span={11}>
            <h3>Income</h3>
            <Form.Item
              name={["income_obj", "monthly_rent"]}
              label="Monthly Rent"
            >
              <InputNumber prefix="$" style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              name={["income_obj", "annual_rent_increase"]}
              label="Annual Rent Increase"
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
              label="Other Income Annual Increase"
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
        <Divider />

        <h3>Recurring Operating Expenses</h3>
        <Row gutter={16}>
          <Col span={11}>
            <Form.Item label="">
              <Row gutter={8}>
                <Col span={12}>
                  <Form.Item name="annual_property_tax" label="Property Tax">
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
            <Divider />
            <Form.Item>
              <Row gutter={8}>
                <Col span={12}>
                  <Form.Item
                    name="annual_total_insurance"
                    label="Total Insurance"
                  >
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
            <Divider />
            <Form.Item label="">
              <Row gutter={8}>
                <Col span={12}>
                  <Form.Item name="annual_hoa" label="HOA Fee">
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
          <Col span={2}>
            <Divider type="vertical" style={{ height: "100%" }} />
          </Col>
          <Col span={11}>
            <Form.Item label="">
              <Row gutter={8}>
                <Col span={12}>
                  <Form.Item name="annual_maintenance" label="Maintenance">
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
            <Divider />
            <Form.Item label="">
              <Row gutter={8}>
                <Col span={12}>
                  <Form.Item name="annual_other_costs" label="Other Costs">
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
        <Divider />
        <h3>Sell</h3>
        <Form.Item label="Do You Know the Sell Price?" valuePropName="checked">
          <Switch checked={knowSellPrice} onChange={setKnowSellPrice} />
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

          <Form.Item label="No Rent Months">
            <Row gutter={8}>
              <Col span={8}>
                <InputNumber
                  placeholder="Start Month"
                  min={1}
                  max={1000}
                  value={startMonth}
                  onChange={setStartMonth}
                />
              </Col>
              <Col span={8}>
                <InputNumber
                  placeholder="End Month"
                  min={1}
                  max={1000}
                  value={endMonth}
                  onChange={setEndMonth}
                />
              </Col>
              <Col span={8}>
                <Button onClick={handleAddNoRentMonths}>
                  Add to No Rent Months
                </Button>
              </Col>
            </Row>
            {noRentMonths.map((tuple, index) => (
              <div key={index}>
                [{tuple[0]}, {tuple[1]}]
                <Button
                  type="link"
                  icon={<CloseOutlined />}
                  onClick={() => handleDeleteNoRentPeriod(index)}
                />
              </div>
            ))}
          </Form.Item>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default PropertyForm;
