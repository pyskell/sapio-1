from sapio_compiler import *
# Demonstrates multisig with a default path accessible at a lower threshold
class DemoLayeredConditions(Contract):
    class Fields:
        key_a: PubKey
        key_b: PubKey
        key_c: PubKey
        key_d: PubKey
        amount: Amount
        setup: TransactionTemplate

    @require
    def a_signed(self) -> Clause:
        return SignatureCheckClause(self.key_a)

    @require
    def two_weeks(self) -> Clause:
        return AfterClause(Weeks(2))

    @require
    def one_month(self: DemoLayeredConditions) -> Clause:
        return AfterClause(Weeks(4))

    @require
    def b_signed(self) -> Clause:
        return SignatureCheckClause(self.key_b)

    @require
    def c_signed(self) -> Clause:
        return SignatureCheckClause(self.key_c)

    @threshold(3, [a_signed, b_signed, c_signed])
    @unlock
    def all_signed(self) -> Clause:
        return SatisfiedClause()

    @threshold(2, [a_signed, b_signed, c_signed])
    @guarantee
    def setup_tx(self) -> TransactionTemplate:
        # maybe make some assertions about timing...
        t: TransactionTemplate = self.setup.assigned_value
        return t

    @a_signed
    @two_weeks
    @unlock
    def time_release(self) -> Clause:
        return SatisfiedClause()

    # This is an issue with MyPy, this composition works fine in practice, but
    # the type checker can't understand for whatever reason see:
    # https://github.com/python/peps/pull/242#issuecomment-619788961 When this
    # is fixed, or we have a workaround, this will type check.
    #
    # Until then, when stacking on top of an @require, .stack must be used in
    # order for it to compose and pass type checks... it's not needed for the
    # program to be correct though.
    #
    # @one_month # broken!
    @one_month.stack
    @require
    def d_signed_and_one_month(self) -> Clause:
        return SignatureCheckClause(self.key_d)

    @d_signed_and_one_month
    @guarantee
    def setup_tx2(self) -> TransactionTemplate:
        # maybe make some assertions about timing...
        t: TransactionTemplate = self.setup.assigned_value
        return t

    @threshold(3, [a_signed, b_signed, c_signed])
    @unlock_but_suggest
    def cooperate_example(
        self, state: Optional[List[Tuple[Amount, str]]] = None,
    ) -> TransactionTemplate:
        if state is None:
            # Default example:
            return self.setup.assigned_value
        else:
            tx = TransactionTemplate()
            tx.add_output(
                self.amount.assigned_value,
                ContractClose(amount=self.amount, payments=state),
            )
            return tx


class ContractClose(Contract):
    class Fields:
        amount: Amount
        payments: List[Tuple[Amount, str]]

    @require
    def wait(self):
        return AfterClause(Weeks(2))

    @wait
    @guarantee
    def make_payments(self) -> TransactionTemplate:
        tx = TransactionTemplate()
        for (amt, to) in self.payments.assigned_value:
            tx.add_output(amt, PayToSegwitAddress(amount=amt, address=to))
        return tx