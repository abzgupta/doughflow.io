import React, { useState, useEffect } from "react";
import axios from "axios";
import PropertyForm from "./PropertyForm";
import BudgetSankey from "./BudgetSankey";
import Disclaimer from "./Disclaimer";

import { DollarTwoTone } from "@ant-design/icons";

import {
  Button,
  message,
  Modal,
  Form,
  Input,
  Row,
  Col,
  InputNumber,
  Statistic,
  Card,
  Table,
} from "antd";
import CountUp from "react-countup";
const formatter = (prevValue, currentValue) => (
  <CountUp start={prevValue} end={currentValue} delay={0} separator="," />
);

const App = () => {
  const [properties, setProperties] = useState([]);
  const [currentMonth, setCurrentMonth] = useState(1);
  const [isAnimationRunning, setIsAnimationRunning] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [consolidatedMonthlyCashflow, setConsolidatedMonthlyCashflow] =
    useState([]);
  const [skipToMonth, setSkipToMonth] = useState(currentMonth);
  const [prevTotalCashFlow, setPrevTotalCashFlow] = useState(0);
  const [currentTotalCashFlow, setCurrentTotalCashFlow] = useState(0);
  const [propertyCards, setPropertyCards] = useState({});
  const [propertiesToSell, setPropertiesToSell] = useState([]);
  const [selectedProperty, setSelectedProperty] = useState(null);

  const columns = [
    { title: "Month", dataIndex: "month_number", key: "month_number" },
    {
      title: "Property Name",
      dataIndex: "property_name",
      key: "property_name",
    },
    {
      title: "Cumulative Cash For Property",
      dataIndex: "cumulative_cash_for_property",
      key: "cumulative_cash_for_property",
    },
    { title: "Property Value", dataIndex: "value", key: "value" },
    {
      title: "Remaining Loan Amount",
      dataIndex: "remaining_loan_amount",
      key: "remaining_loan_amount",
    },
    {
      title: "If Sold Today",
      dataIndex: "if_sold_today",
      key: "if_sold_today",
    },
  ];

  useEffect(() => {
    if (properties.length > 0) {
      callFlaskApi();
    }
  }, [properties]);

  useEffect(() => {
    const filteredCashflow = consolidatedMonthlyCashflow.filter(
      (item) => item.month_number === currentMonth
    );

    const filteredCashflowOverall = consolidatedMonthlyCashflow.filter(
      (item) =>
        item.month_number === currentMonth && item.property_name == "Overall"
    );

    const unsoldProperties = filteredCashflow.filter(
      (item) => item.is_sold === 0 && item.property_name !== "Overall"
    );
    setPropertiesToSell(unsoldProperties);

    console.log(currentMonth, "here", filteredCashflow);
    let updatedPropertyCards = {};
    properties.forEach((property) => {
      const latestRecord = consolidatedMonthlyCashflow.reduce(
        (latest, item) => {
          if (
            item.property_name === property.property_name &&
            item.month_number <= currentMonth &&
            item.month_number > (latest ? latest.month_number : 0)
          ) {
            return item;
          }
          return latest;
        },
        null
      );

      if (latestRecord) {
        updatedPropertyCards[property.property_name] = {
          monthly_rent: latestRecord.monthly_rent,
          cashflow_after_expenses: latestRecord.cash_flow,
          cumulative_cash_for_property:
            latestRecord.cumulative_cash_for_property,
          value: latestRecord.value,
          remaining_loan_amount: latestRecord.remaining_loan_amount,
          if_sold_today: latestRecord.if_sold_today,
          cash_on_cash_return: latestRecord.cash_on_cash_return,
          cash_on_cash_return_if_sold_today:
            latestRecord.cash_on_cash_return_if_sold_today,
        };
      }
    });

    if (filteredCashflowOverall.length > 0) {
      const totalCashFlow =
        filteredCashflowOverall[0].cumulative_cash_for_property;
      setPrevTotalCashFlow(currentTotalCashFlow);
      setCurrentTotalCashFlow(totalCashFlow);

      // Update the propertyCards state
    }
    setPropertyCards(updatedPropertyCards);
  }, [consolidatedMonthlyCashflow, currentMonth]);

  const handleEditProperty = (property) => {
    const selectedFilteredProperty = properties.filter(
      (x) => x.property_name == property.property_name
    );
    const selectedFilteredPropertyValue = selectedFilteredProperty[0];
    console.log(selectedFilteredPropertyValue);
    selectedFilteredPropertyValue.holding_length =
      selectedFilteredPropertyValue.original_holding_length / 12;
    setSelectedProperty(selectedFilteredPropertyValue);
    setIsModalVisible(true);
  };

  const handleSellProperty = (propertyName) => {
    const updatedProperties = properties.map((property) => {
      if (property.property_name === propertyName) {
        return {
          ...property,
          holding_length: currentMonth - property.month_offset,
          is_sold: true,
        };
      }
      return property;
    });

    setPropertiesToSell([]);
    setProperties(updatedProperties);
  };

  const handleCreate = (values) => {
    console.log("Received values of form: ", values);
    const filteredProperties = properties.filter(
      (x) => x.property_name != values["property_name"]
    );
    setProperties([...filteredProperties, values]);
    setSelectedProperty(null);
    setIsModalVisible(false);
  };

  const callFlaskApi = async () => {
    try {
      console.log(properties);
      const response = await axios.post(
        "https://abzgupta.pythonanywhere.com/get_financial_table_summarized",
        {
          property_list: properties,
        },
        {
          headers: {
            "Content-Type": "application/json",
          },
        }
      );
      console.log(response);

      // Check if the response data is a string
      if (typeof response.data === "string") {
        // Parse the string to extract the actual data
        const parsedData = JSON.parse(response.data);
        setConsolidatedMonthlyCashflow(parsedData.data);
      } else {
        // If the response data is already an array, use it directly
        setConsolidatedMonthlyCashflow(response.data);
      }
    } catch (error) {
      if (error.response) {
        console.error("Error calling Flask API:", error.response.data);
        console.error("Status code:", error.response.status);
        console.error("Headers:", error.response.headers);
      } else if (error.request) {
        console.error("No response received from the server:", error.request);
      } else {
        console.error("Error setting up the request:", error.message);
      }
    }
  };

  useEffect(() => {
    let timer = null;
    if (isAnimationRunning) {
      timer = setInterval(() => {
        setCurrentMonth((prevMonth) => prevMonth + 1);
      }, 2000); // Adjust the interval duration as needed
    }
    return () => clearInterval(timer);
  }, [isAnimationRunning]);

  const handleStartPauseClick = () => {
    setIsAnimationRunning((prevState) => !prevState);
  };

  const handleSkipToMonthChange = (value) => {
    setSkipToMonth(value);
  };

  const handleSkipToMonthSubmit = () => {
    setCurrentMonth(skipToMonth);
  };

  return (
    <Row gutter={[16, 16]}>
      <Col span={12}>
        <Row>
          <Col span={8} />
          <Col span={8}>
            {" "}
            <Statistic title="Month Number" value={currentMonth} />
          </Col>
          <Col span={8} />
        </Row>

        <Button onClick={handleStartPauseClick}>
          {isAnimationRunning ? "Pause" : "Start"}
        </Button>
        <Button
          onClick={() => setIsModalVisible(true)}
          disabled={isAnimationRunning}
        >
          Purchase Property
        </Button>
        {!isAnimationRunning && (
          <div style={{ display: "inline-block", marginLeft: "10px" }}>
            <InputNumber
              min={0}
              value={skipToMonth}
              onChange={handleSkipToMonthChange}
              style={{ width: "120px" }}
            />
            <Button
              onClick={handleSkipToMonthSubmit}
              style={{ marginLeft: "10px" }}
            >
              Skip to this month
            </Button>
          </div>
        )}
        <PropertyForm
          visible={isModalVisible}
          onCreate={handleCreate}
          onCancel={() => {
            setSelectedProperty(null);
            setIsModalVisible(false);
          }}
          currentMonth={currentMonth}
          initialValues={selectedProperty}
          propertyCount={properties.length}
        />
        {!isAnimationRunning && propertiesToSell.length > 0 && (
          <div>
            <h3>Properties to Sell</h3>
            <ul>
              {propertiesToSell.map((property) => (
                <li key={property.property_name}>
                  {property.property_name}{" "}
                  <Button
                    onClick={() => handleSellProperty(property.property_name)}
                  >
                    Sell?
                  </Button>
                  <Button onClick={() => handleEditProperty(property)}>
                    Edit Property
                  </Button>
                </li>
              ))}
            </ul>
          </div>
        )}
        <div>
          <h3>Property Statistics</h3>
          <Card>
            <Statistic
              title="Cashflow"
              value={currentTotalCashFlow}
              formatter={() =>
                formatter(prevTotalCashFlow, currentTotalCashFlow)
              }
            />
          </Card>
          <Row gutter={[16, 16]}>
            {Object.entries(propertyCards).map(
              ([propertyName, propertyStats]) => (
                <Col key={propertyName} span={6}>
                  <Card bordered={true}>
                    <h2>{propertyName}</h2>
                    <Statistic
                      title="Monthly Rent"
                      value={propertyStats.monthly_rent}
                      formatter={(value) =>
                        Math.round(value).toLocaleString("en-US", {
                          style: "currency",
                          currency: "USD",
                          minimumFractionDigits: 0,
                          maximumFractionDigits: 0,
                        })
                      }
                    />
                    <Statistic
                      title="Monthly Cashflow net Expenses"
                      value={propertyStats.cashflow_after_expenses}
                      formatter={(value) =>
                        Math.round(value).toLocaleString("en-US", {
                          style: "currency",
                          currency: "USD",
                          minimumFractionDigits: 0,
                          maximumFractionDigits: 0,
                        })
                      }
                    />
                    <Statistic
                      title="Cumulative Cash"
                      value={propertyStats.cumulative_cash_for_property}
                      formatter={(value) =>
                        Math.round(value).toLocaleString("en-US", {
                          style: "currency",
                          currency: "USD",
                          minimumFractionDigits: 0,
                          maximumFractionDigits: 0,
                        })
                      }
                    />
                    <Statistic
                      title="Property Value"
                      value={propertyStats.value}
                      formatter={(value) =>
                        Math.round(value).toLocaleString("en-US", {
                          style: "currency",
                          currency: "USD",
                          minimumFractionDigits: 0,
                          maximumFractionDigits: 0,
                        })
                      }
                    />
                    <Statistic
                      title="Remaining Loan Amount"
                      value={propertyStats.remaining_loan_amount}
                      formatter={(value) =>
                        Math.round(value).toLocaleString("en-US", {
                          style: "currency",
                          currency: "USD",
                          minimumFractionDigits: 0,
                          maximumFractionDigits: 0,
                        })
                      }
                    />
                    <Statistic
                      title="If Sold Today"
                      value={propertyStats.if_sold_today}
                      formatter={(value) =>
                        Math.round(value).toLocaleString("en-US", {
                          style: "currency",
                          currency: "USD",
                          minimumFractionDigits: 0,
                          maximumFractionDigits: 0,
                        })
                      }
                    />
                    <Statistic
                      title="Cash on Cash Return"
                      value={propertyStats.cash_on_cash_return}
                      formatter={(value) =>
                        (value * 100).toLocaleString("en-US", {
                          style: "decimal",
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        }) + "%"
                      }
                    />
                    <Statistic
                      title="Cash on Cash Return If Sold Today"
                      value={propertyStats.cash_on_cash_return_if_sold_today}
                      formatter={(value) =>
                        (value * 100).toLocaleString("en-US", {
                          style: "decimal",
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        }) + "%"
                      }
                    />
                  </Card>
                </Col>
              )
            )}
          </Row>
        </div>
      </Col>
      <Col span={12}>
        <div>
          <h3>Consolidated Monthly Cashflow</h3>
          <Table
            dataSource={consolidatedMonthlyCashflow}
            columns={columns}
            pagination={true}
            rowKey="month_number"
          />
        </div>
      </Col>
      <Row>
        <Col span={4}></Col>
        <Col span={16}>
          <Disclaimer/>
        </Col>
        <Col span={4}></Col>
      </Row>
    </Row>
  );
};

export default App;
