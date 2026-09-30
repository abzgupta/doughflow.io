import React from 'react';

const Disclaimer = () => {
  return (
    <div className="disclaimer">
      <h2>Disclaimer</h2>
      <p>
        DoughFlow is an educational tool. It is not financial, investment, tax, or legal advice.
        The simulations are simplified models built on hypothetical assumptions. They may contain
        errors and will not match real-world outcomes. Tax calculations are rough estimates based
        on simplified rules that may be out of date or wrong for your situation.
      </p>
      <p>
        Before making any financial decision, consult a qualified financial advisor, a tax advisor
        or CPA, and where relevant an attorney, who can account for your specific circumstances.
        DoughFlow is not a substitute for professional advice.
      </p>
      <p>
        You use DoughFlow entirely at your own risk and are solely responsible for any decisions you
        make. The developers and contributors are not liable for any financial loss or other damages
        arising from your use of the app or your reliance on its output. The software is provided
        "as is", without warranty of any kind.
      </p>
    </div>
  );
};

export default Disclaimer;
