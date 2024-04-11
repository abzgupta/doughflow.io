import numpy as np
import json
import random
import pandas as pd
import copy 


def calculate_rental_income(rental_obj,month_offset=0):
    
    
    def calculate_down_payment_amount(rental_obj):
        """
            down_payment_amount = purchase value * down payment pct
        """
        purchase_price = rental_obj['purchase_price']
        down_payment_pct = rental_obj['loan_obj']['down_payment_pct'] / 100.0

        down_payment_amount = purchase_price * down_payment_pct
        return down_payment_amount

    def calculate_initial_costs(rental_obj):
        initial_costs = 0
        """
            initial costs = down_payment + closing_cost + repair costs
        """
        down_payment_amount = calculate_down_payment_amount(rental_obj)
        repair_costs = rental_obj['repairs_obj']['repair_cost']
        closing_costs = rental_obj['closing_cost']
        return down_payment_amount + repair_costs + closing_costs

    def get_loan_amount(rental_object):
        purchase_price = rental_obj['purchase_price']
        down_payment_amount = calculate_down_payment_amount(rental_obj)
        loan_amount = purchase_price - down_payment_amount
        return loan_amount

    def calculate_monthly_payment_amount(rental_obj):
        loan_amount = get_loan_amount(rental_obj)
        rate = rental_obj['loan_obj']['interest_rate_pct'] / 100
        loan_term = rental_obj['loan_obj']['loan_term']
        c = rate / 12.0
        n = rental_obj['loan_obj']['loan_term']*12
        L = loan_amount
        monthly_payment_amount = L * (c * (1 + c) ** n) / ((1 + c) ** n - 1)
        return monthly_payment_amount

    def break_down_interest_and_principal(rental_obj):
        rows = []
        amt = calculate_monthly_payment_amount(rental_obj)
        loan_amount = get_loan_amount(rental_obj)
        L = loan_amount
        holding_length = rental_obj['holding_length']
        n = holding_length
        for i in range(1, n + 1): 
            if i<=rental_obj['loan_obj']['loan_term']*12:
                rate = rental_obj['loan_obj']['interest_rate_pct'] / 100
                interest = (L * rate) / 12.0
                principal = amt - interest
                L = L - principal
            else: 
                rate = 0 
                interest = 0 
                principal = 0 
                L = 0
            rows.append((i, 'interest', interest))
            rows.append((i, 'principal', principal))
            rows.append((i, 'remaining_loan_amount', L))
        return rows

    def get_annual_expenses(rental_obj):
        rows = []
        expenses_list = [
            'annual_property_tax',
            'annual_total_insurance',
            'annual_hoa',
            'annual_other_costs',
            'annual_maintenance'
        ]
        holding_length = rental_obj['holding_length']
        for i in range(1, holding_length+ 1):
            for exp in expenses_list:
                exp_pct = exp + '_increase_pct'
                amt = rental_obj[exp] * (1 + rental_obj[exp_pct] / 100.) ** ((i // 12))
                if i % 12 == 1:
                    rows.append((i, exp, amt))
                else:
                    rows.append((i, exp, 0))
        return rows

    def get_no_rent_months_flat(rental_obj):
        no_rent_months = rental_obj.get('no_rent_months', [])
        flatten_no_rent_months = []
        for period in no_rent_months:  
            start_p, end_p = period
            flatten_no_rent_months.extend(range(start_p, end_p+1)) 
        return set(flatten_no_rent_months)
    
    def get_monthly_income(rental_obj): 
        no_rent_months_set = get_no_rent_months_flat(rental_obj)
        rows = []
        monthly_rent = rental_obj['income_obj']['monthly_rent'] / ((1 + rental_obj['income_obj']['annual_rent_increase'] / 100.0))
        other_income = rental_obj['income_obj']['other_monthly_income']
        vacancy_rate = rental_obj['income_obj']['vacancy_rate_pct'] / 100.0
        management_fee = rental_obj['income_obj']['management_fee'] / 100.0
        holding_length = rental_obj['holding_length']
        for i in range(1, holding_length + 1):
            if i % 12 == 1:
                monthly_rent = monthly_rent * (1 + rental_obj['income_obj']['annual_rent_increase'] / 100.0)
                other_income = other_income * (1 + rental_obj['income_obj']['other_monthly_income_increase'] / 100.0)
            if i not in no_rent_months_set:
                rows.append((i, 'monthly_rent', monthly_rent))
                rows.append((i, 'monthly_rent_income', monthly_rent * (1 - management_fee)))
                rows.append((i, 'other_income', other_income))
                rows.append((i, 'management_fee', management_fee * monthly_rent))
                rows.append((i, 'is_occupied', 1))
            else:
                rows.append((i, 'monthly_rent', monthly_rent))
                rows.append((i, 'monthly_rent_income', 0))
                rows.append((i, 'other_income', 0))
                rows.append((i, 'management_fee', 0))
                rows.append((i, 'is_occupied', 0))
        return rows

    def get_value_increase(rental_obj):
        rows = []
        value_increase = rental_obj['value_appreciation_per_year_pct'] / 100.
        purchase_price = rental_obj['purchase_price']
        holding_length = rental_obj['holding_length']
        base = purchase_price
        if rental_obj['repairs_obj'] and rental_obj:
            new_purchase_price = rental_obj['repairs_obj'].get('value_after_repair',0)
            base = max(purchase_price, new_purchase_price)
        for i in range(1, holding_length + 1):
            j = i // 12
            rows.append((i, 'value', base * ((1 + value_increase) ** (j))))
        return rows

    def consolidate_transations(rental_obj):
        rows = {}
        holding_length = rental_obj['holding_length']
        for i in range(1, holding_length + 1):
            rows[i] = {
                'month_number': i
            }

        income_rows = get_monthly_income(rental_obj)
        outflow_rows = break_down_interest_and_principal(rental_obj)
        expense_rows = get_annual_expenses(rental_obj)
        value_increase = get_value_increase(rental_obj)
        income_rows.extend(outflow_rows)
        income_rows.extend(expense_rows)
        income_rows.extend(value_increase)

        initial_costs = calculate_initial_costs(rental_obj)
        multiplier = 0
        if month_offset >= 0:
            multiplier = 1
        for i, r in enumerate(income_rows):
            month_number = r[0]
            row_obj = rows[month_number]
            row_obj[r[1]] = r[2]
            if month_number == 1:
                row_obj['initial_costs'] = initial_costs * multiplier
            else:
                row_obj['initial_costs'] = 0

        rental_df = pd.DataFrame(rows.values())
        rental_df['purchase_price'] = rental_obj['purchase_price']

        column_order = ['month_number', 'purchase_price', 'initial_costs','monthly_rent', 'monthly_rent_income', 'other_income',
                        'management_fee', 'is_occupied', 'annual_hoa', 'annual_maintenance',
                        'annual_other_costs', 'annual_property_tax', 'annual_total_insurance',
                        'interest', 'principal', 'remaining_loan_amount', 'value']

        rental_df = rental_df[column_order] 
        rental_df['is_sold'] = rental_df['month_number'] == rental_obj['holding_length']
        rental_df['month_number'] = rental_df['month_number'] + month_offset 
        rental_df['holding_length'] = rental_obj['holding_length']
        rental_df['cost_to_sell_pct'] = rental_obj['cost_to_sell_pct']
        
        return rental_df

    return consolidate_transations(rental_obj)

def my_adjust_transaction_obj_for_new_purchase(original_obj, month_offset=0): 
    if month_offset == 0: 
        return original_obj.copy()
    adjusted_obj = original_obj.copy()  # Make a copy to avoid mutating the original object
    #print(adjusted_obj['income_obj']['monthly_rent'], month_offset)
    # Calculate the number of years from month_offset
    years_offset = month_offset / 12
    

    # Adjust the purchase price based on appreciation
    value_appreciation_rate = adjusted_obj['value_appreciation_per_year_pct'] / 100
    adjusted_obj['purchase_price'] *= (1 + value_appreciation_rate) ** years_offset

    # Adjustments based on the new purchase price
    # Note: Some adjustments like closing_cost and repair_cost might not be directly proportional
    # to the purchase price and could depend on other factors. Adjust them as per your assumptions.
    down_payment_pct = adjusted_obj['loan_obj']['down_payment_pct'] / 100
    adjusted_obj['loan_obj']['down_payment_amount'] = adjusted_obj['purchase_price'] * down_payment_pct
    adjusted_obj['repairs_obj']['repair_cost'] = adjusted_obj['purchase_price'] * 3/100  # Adjust based on your assumptions
    adjusted_obj['repairs_obj']['value_after_repair'] = adjusted_obj['purchase_price'] *1.25  # Adjust based on your assumptions

    # Adjust income and expenses that are related to the property value
    # For example, property tax, insurance, HOA fees, etc., might be recalculated based on the new value
    adjusted_obj['annual_property_tax'] = adjusted_obj['annual_property_tax'] * (1 + adjusted_obj['annual_property_tax_increase_pct'] / 100) ** years_offset
    adjusted_obj['annual_total_insurance'] = adjusted_obj['annual_total_insurance'] * (1 + adjusted_obj['annual_total_insurance_increase_pct'] / 100) ** years_offset
    adjusted_obj['annual_hoa'] = adjusted_obj['annual_hoa'] * (1 + adjusted_obj['annual_hoa_increase_pct'] / 100) ** years_offset
    # Other adjustments as necessary

    # Adjust rental income based on market conditions
    #print(adjusted_obj['income_obj']['monthly_rent'], (1 + adjusted_obj['income_obj']['annual_rent_increase'] / 100) , years_offset)
    adjusted_obj['income_obj']['monthly_rent'] = adjusted_obj['income_obj']['monthly_rent'] * (1 + adjusted_obj['income_obj']['annual_rent_increase'] / 100) ** years_offset
    # Adjust other income fields similarly

    return adjusted_obj


    



def calculate_hypothetical_cost_to_purchase(rental_obj, month_offset): 
    new_rental_obj = copy.deepcopy(rental_obj)  # Use deepcopy instead of copy

    #print(new_rental_obj['income_obj']['monthly_rent'], month_offset)
    adjusted_obj = my_adjust_transaction_obj_for_new_purchase(new_rental_obj, month_offset)

    # Calculate the down payment amount based on the adjusted purchase price
    down_payment_pct = adjusted_obj['loan_obj']['down_payment_pct'] / 100
    adjusted_purchase_price = adjusted_obj['purchase_price']
    down_payment_amount = adjusted_purchase_price * down_payment_pct

    # Calculate the total cost of purchasing the property
    repair_cost = adjusted_obj['repairs_obj']['repair_cost']
    closing_cost = adjusted_obj['closing_cost']
    total_cost = down_payment_amount + repair_cost + closing_cost

    return total_cost
    
def get_adjusted_hypothetical_purchase_price(flag): 
    if flag is True: 
        return float('inf')
    else:
        return 1



def get_financial_table(property_list):
    expenses_list = ['annual_property_tax',
                     'annual_total_insurance',
                     'annual_hoa',
                     'annual_other_costs',
                     'annual_maintenance',
                     'initial_costs', 
                     'management_fee'
                     ]
    rental_df_list = []
    rental_df = None
    for i, purchase_obj in enumerate(property_list):
        month_offset = purchase_obj['month_offset']
        current_df = calculate_rental_income(purchase_obj, month_offset)
        current_df['property_number'] = i+1
        current_df['property_name'] = purchase_obj['property_name']
        current_df = current_df.sort_values(by=['month_number', 'property_number'])
        current_df['mortgage_due'] = current_df['interest'] + current_df['principal']
        current_df['total_income_for_month'] = current_df['monthly_rent_income'] + current_df['other_income']
        current_df['total_cost_for_month'] = sum([current_df[x] for x in expenses_list])

        # Calculate selling costs (assuming a percentage of the property value)
        current_df['selling_costs'] = current_df['value'] * current_df['cost_to_sell_pct'] / 100.0

        current_df['if_sold_today'] = current_df['value'] - current_df['remaining_loan_amount'] - current_df['selling_costs']
        current_df['cash_flow'] = current_df['total_income_for_month'] - (current_df['total_cost_for_month'] + current_df['mortgage_due'])
        current_df.loc[current_df['is_sold'], 'cash_flow'] = current_df.loc[current_df['is_sold'], 'if_sold_today']
        current_df['cumulative_cash_for_property'] = current_df.groupby('property_number')['cash_flow'].cumsum()
        current_df['cumulative_expenses'] = current_df['total_cost_for_month'].cumsum()
        current_df['cumulative_cash_for_property_if_sold_today']= current_df['cumulative_cash_for_property'] + current_df['if_sold_today']
        current_df['multiplier'] = float("inf")
        current_df['adj_hypothetical_cost_to_purchase_next_property'] = float("inf")
        current_df['cash_on_cash_return'] = current_df['cumulative_cash_for_property'] / current_df['cumulative_expenses'] 
        current_df['cash_on_cash_return_if_sold_today'] = (current_df['cumulative_cash_for_property'] + current_df['if_sold_today']) / current_df['cumulative_expenses']
        rental_df_list.append(current_df)
        
        
    rental_df = pd.concat(rental_df_list)
    rental_df['hypothetical_cost_to_purchase_next_property'] = float('inf')
    # Group by month_number and sum all numerical columns
    overall_df = rental_df.groupby('month_number').sum().reset_index()
    overall_df['property_number'] = len(rental_df_list) + 1
    overall_df['multiplier'] = 1
    overall_df['adj_hypothetical_cost_to_purchase_next_property'] = 1
    overall_df['property_name'] = 'Overall'

    hypothetical_cost_to_purchase_next_property_list = [calculate_hypothetical_cost_to_purchase(purchase_obj, month) for month in overall_df.month_number.values.tolist()]
    overall_df['hypothetical_cost_to_purchase_next_property'] = hypothetical_cost_to_purchase_next_property_list

    # Combine the rental_df and overall_df
    final_df = pd.concat([rental_df, overall_df])
    final_df = final_df.sort_values(by=['month_number', 'property_number'])

    return final_df

def sum_up_financials(rental_df):
    expenses_list = ['annual_property_tax',
                     'annual_total_insurance',
                     'annual_hoa',
                     'annual_other_costs',
                     'annual_maintenance',
                     'initial_costs', 
                     'management_fee'
                     ]
    
    max_property_number = max(rental_df['property_number'])
    rental_df = rental_df.sort_values(by=['month_number', 'property_number'])
    
    # Calculate cumulative cash for each property
    
    # Filter the DataFrame to get the rows where cumulative_cash exceeds the hypothetical cost to purchase the next property
    #next_month_offset = min(rental_df[rental_df['cumulative_cash'] >= rental_df.adj_hypothetical_cost_to_purchase_next_property].month_number)
    
    return rental_df

def get_financial_table_summarized(property_list):
    rental_df = get_financial_table(property_list)
    final_df = sum_up_financials(rental_df)
    return final_df