# Builds the guided walkthrough notebook. Run once with: python build_notebook.py
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []


def md(text):
    cells.append(nbf.v4.new_markdown_cell(text))


def code(text=''):
    cells.append(nbf.v4.new_code_cell(text))


md("""# Bertus Delivery Performance Walkthrough

A simple, guided operations and logistics data project, built with pandas and matplotlib,
the same tools Codecademy's data analyst path teaches.

**Goal:** answer three real operations questions from the data.
1. How reliable are our deliveries overall.
2. Which delay reasons hurt us most.
3. Which carrier is actually the weak link.

**How to use this notebook**
* Run the cells from top to bottom, in order, each one builds on the last.
* Where you see `# TODO`, that is your part, write the code yourself. A hint comment
  tells you which pandas or matplotlib method to use, it does not give you the answer.
* If you get stuck, `bertus_shipments_raw.csv` is the only file this notebook reads.
  Open it in Excel first if it ever helps to just look at the raw rows.
* The finished `Bertus Delivery Performance Dashboard (finished reference example).xlsx`
  in this same folder shows roughly what your final numbers should look like, use it to
  check your work, not to copy from.
""")

code("""# Setup. If either import fails, run this first in a terminal:
#   python -m pip install pandas matplotlib
import pandas as pd
import matplotlib.pyplot as plt
""")

md("""## Step 1. Load the data

The raw file is `bertus_shipments_raw.csv`, sitting in this same folder.

**TODO:** read it into a DataFrame called `df`, then print the first 5 rows to make sure
it loaded correctly.

Hint: `pd.read_csv(...)` and `df.head()`.
""")

code("""# TODO: load bertus_shipments_raw.csv into df, then look at the first few rows
df = None  # replace this
""")

md("""## Step 2. Look at what you actually have

Before cleaning anything, get a feel for the data.

**TODO:**
* Print `df.info()` to see column names, types and whether anything is missing.
* Print how many unique values are in `carrier` and `customer_type`.

Hint: `df['carrier'].unique()` and `df['carrier'].nunique()`.
""")

code("""# TODO: explore df with .info() and .unique() on a couple of columns
""")

md("""## Step 3. Clean the dates

Right now `order_date`, `promised_delivery_date` and `actual_delivery_date` are plain
text, not real dates, so you cannot do date math on them yet.

**TODO:** convert all three columns to real dates in place.

Hint: `pd.to_datetime(df['order_date'])`, do the same for the other two date columns.
""")

code("""# TODO: convert the three date columns to datetime
""")

md("""## Step 4. Work out if each shipment was late

This is the core feature engineering step. From the two delivery dates, you can work
out how late something was, and whether it was on time at all.

**TODO:**
* Create a new column `delay_days` equal to `actual_delivery_date` minus
  `promised_delivery_date`, in days as a plain number.
* Create a new column `on_time` that is `True` when `delay_days` is 0 or less,
  `False` otherwise.

Hint: subtracting two datetime columns gives you a `Timedelta`, use `.dt.days` to turn
that into a plain number.
""")

code("""# TODO: create delay_days and on_time columns
""")

md("""## Step 5. Add a month column

To see a trend over time later, you need something to group by month.

**TODO:** create a column `order_month` from `order_date`, formatted like `Apr-26`.

Hint: `.dt.strftime('%b-%y')`.
""")

code("""# TODO: create order_month
""")

md("""## Step 6. The headline numbers

Now the real analysis starts. These are the numbers you would open a meeting with.

**TODO:** print all four of these.
* Total number of shipments.
* Overall on time rate, as a percentage.
* Average delay in days, counting only the shipments that were actually late.
* Total order value in euros.

Hint: `len(df)`, `df['on_time'].mean()` gives you a rate between 0 and 1, and filtering
with `df[df['delay_days'] > 0]` gets you just the late ones before averaging.
""")

code("""# TODO: print total shipments, on time rate, average delay for late shipments,
# and total order value
""")

md("""## Step 7. Which delay reason hurts us most

Every late shipment has a `delay_reason`. On time shipments have an empty one.

**TODO:** build a table showing, for each real delay reason, how many shipments it
caused and what percent of all delayed shipments that is.

Hint: filter out the empty reason first, then `.groupby('delay_reason').size()`, then
divide by the total number of delayed shipments.
""")

code("""# TODO: delay reason breakdown, count and percent of delayed shipments
""")

md("""## Step 8. Which carrier is the weak link

**TODO:** build a table with one row per carrier showing: total shipments handled,
on time rate, and average delay in days.

Hint: `.groupby('carrier')` then use `.agg(...)` with a dictionary to compute several
things at once, for example counting shipments and averaging `on_time` and
`delay_days` in the same call.
""")

code("""# TODO: carrier performance table
""")

md("""## Step 9. The monthly trend

**TODO:** build a table with one row per month (using `order_month`) showing total
shipments and on time rate for that month. Keep the months in real calendar order,
not alphabetical order.

Hint: group by `order_month`, then reindex or sort using the real month order
(`Apr-26`, `May-26`, `Jun-26`, `Jul-26`, `Aug-26`) rather than trusting the default
sort.
""")

code("""# TODO: monthly shipments and on time rate, in real calendar order
""")

md("""## Step 10. Turn the three tables into charts

**TODO:** make three separate matplotlib charts.
1. A bar chart of delay reason versus percent of delayed shipments, from Step 7.
2. A bar chart of carrier versus on time rate, from Step 8, this is the one that
   actually points at the weak carrier.
3. A line chart of month versus on time rate, from Step 9, to show whether
   reliability is improving or getting worse over time.

Hint: `plt.bar(x, y)` or `plt.plot(x, y)`, then `plt.title(...)`, `plt.xlabel(...)`,
`plt.ylabel(...)` and `plt.show()` for each one.
""")

code("""# TODO: chart 1, delay reason breakdown
""")

code("""# TODO: chart 2, carrier on time rate comparison
""")

code("""# TODO: chart 3, monthly on time rate trend
""")

md("""## Step 11. Your takeaway

Write two or three sentences here, in your own words, as if you were about to say
this out loud in the interview.

* What is the single biggest driver of delays.
* Which carrier would you actually raise as a concern, and why, using the real
  number you calculated.
* One concrete idea to fix it, for example a shared delay log visible to warehouse,
  carriers and customer facing staff at the same time.

*(Write your answer here once the analysis above is done.)*
""")

nb['cells'] = cells
nbf.write(nb, 'Bertus_Delivery_Walkthrough.ipynb')
print('Written: Bertus_Delivery_Walkthrough.ipynb')
