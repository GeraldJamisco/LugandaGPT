"""English source examples for formal comprehension and generation."""

from source_pilot_common import item

PILOT = [
    item(
        "P-001",
        "pilot",
        "formal_comprehension",
        "Using only the notice, state when the library opens on Saturday and what visitors must bring.",
        [
            "States that the library opens at nine in the morning.",
            "States that visitors must bring a current membership card.",
            "Does not add opening times or requirements that are absent from the notice.",
        ],
        "english_reference",
        "The library opens at nine in the morning on Saturday, and visitors must bring a current membership card.",
        split="train",
        context=(
            "The central library will open at nine in the morning on Saturday. "
            "The reading room closes at one in the afternoon. Visitors must bring "
            "a current membership card. Children under twelve must be accompanied "
            "by an adult. The notice was posted at the main entrance."
        ),
        constraints=[
            "Use only the information in the notice.",
            "Mention both the opening time and the required item.",
        ],
        secondary=["question_answering"],
        notes="Short extract-and-answer task with two required details.",
    ),
    item(
        "P-002",
        "pilot",
        "formal_comprehension",
        "Summarize the main decision from the meeting notes in two or three sentences.",
        [
            "Identifies the decision to repair the water pump before the dry season.",
            "Mentions that the community will contribute labor and a small fund.",
            "Does not describe proposals that were rejected.",
        ],
        "english_reference",
        "The meeting agreed to repair the water pump before the dry season. Community members will provide labor and contribute to a small repair fund. The proposal to buy a new pump was postponed.",
        split="heldout",
        context=(
            "At the community meeting, members discussed the broken water pump. "
            "The treasurer reported that a new pump would cost more than the "
            "current fund. Members agreed to repair the existing pump before the "
            "dry season. Each household will provide one day of labor, and a "
            "small repair fund will be opened at the local savings office. The "
            "proposal to buy a new pump was postponed until the next year."
        ),
        constraints=["Write two or three complete sentences."],
        response_length="multi_sentence",
        secondary=["question_answering"],
        notes="Summary task with a rejected proposal as a distractor.",
    ),
    item(
        "P-003",
        "pilot",
        "formal_comprehension",
        "What reason does the email give for moving the staff meeting, and what should staff do before the new time?",
        [
            "Explains that the meeting moved because the main room is being repaired.",
            "States that staff should send agenda items before Friday noon.",
            "Does not claim a different reason or deadline.",
        ],
        "english_reference",
        "The meeting moved because the main room is being repaired. Staff should send agenda items before Friday noon.",
        split="train",
        context=(
            "The weekly staff meeting will move from Monday morning to Tuesday "
            "afternoon because the main room is being repaired. Please send any "
            "agenda items to the office before Friday noon. The meeting will be "
            "held in the small training room. Bring your own notebook."
        ),
        constraints=["Answer both parts of the question."],
        secondary=["question_answering"],
        notes="Two-part extraction task with a changed schedule.",
    ),
    item(
        "P-004",
        "pilot",
        "formal_comprehension",
        "According to the clinic instructions, what should a patient do before the appointment and what should the patient bring?",
        [
            "States that the patient should arrive fifteen minutes early.",
            "States that the patient should bring a medicine list and an identity document.",
            "Does not invent a fee or a different arrival time.",
        ],
        "english_reference",
        "The patient should arrive fifteen minutes early and bring a list of current medicines and an identity document.",
        split="train",
        context=(
            "Patients should arrive fifteen minutes before the appointment time. "
            "Bring a list of all current medicines and one identity document. "
            "The clinic does not accept walk-in patients on Friday afternoons. "
            "If you cannot attend, call the reception desk before the appointment."
        ),
        constraints=[
            "Use only the clinic instructions.",
            "Give both requested details.",
        ],
        secondary=["instruction_following"],
        notes="Everyday health administration context without personal data.",
    ),
    item(
        "P-005",
        "pilot",
        "formal_comprehension",
        "Explain the main problem described in the school notice and the two steps parents are asked to take.",
        [
            "Identifies the problem as a shortage of textbooks.",
            "Mentions returning borrowed books and checking the family contact details.",
            "Does not blame a named person or add an unstated cause.",
        ],
        "english_reference",
        "The school has a shortage of textbooks. Parents are asked to return any borrowed books and to check that the family contact details at the office are correct.",
        split="heldout",
        context=(
            "The school is reviewing its textbook supply because some classes "
            "have fewer books than learners. Parents are asked to return any "
            "borrowed textbooks by the end of the month. The office also asks "
            "families to check that their contact details are correct. A full "
            "report will be shared at the next parents meeting."
        ),
        constraints=["Write at least two sentences."],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Problem-and-action comprehension task.",
    ),
    item(
        "P-006",
        "pilot",
        "formal_comprehension",
        "Using the timetable, say which bus leaves after ten in the morning and how long the journey takes.",
        [
            "Identifies the ten thirty bus.",
            "States that the journey takes one hour and twenty minutes.",
            "Does not choose the nine fifteen or eleven fifteen service.",
        ],
        "english_reference",
        "The ten thirty bus leaves after ten in the morning and takes one hour and twenty minutes.",
        split="train",
        context=(
            "The morning bus timetable lists three departures. The nine fifteen "
            "service takes one hour and ten minutes. The ten thirty service takes "
            "one hour and twenty minutes. The eleven fifteen service takes one "
            "hour and thirty minutes. All buses leave from the main stage."
        ),
        constraints=["Choose one departure and state its journey time."],
        secondary=["question_answering"],
        notes="Simple timetable comparison with distractors.",
    ),
    item(
        "P-007",
        "pilot",
        "formal_comprehension",
        "What is the cooperative asking members to do, and what will happen if the target is not reached?",
        [
            "States that members are asked to pay their monthly contribution early.",
            "Explains that the planned purchase will be delayed if the target is not reached.",
            "Does not invent a penalty or a different target.",
        ],
        "english_reference",
        "Members are asked to pay their monthly contribution early. If the target is not reached, the planned purchase of new storage containers will be delayed.",
        split="train",
        context=(
            "The water cooperative is collecting monthly contributions early this "
            "month. The goal is to buy new storage containers before the rainy "
            "season. Members who pay by the tenth day will help the cooperative "
            "place the order on time. If the target is not reached, the purchase "
            "will be delayed. No extra fee is being introduced."
        ),
        constraints=["Answer both questions."],
        secondary=["question_answering"],
        notes="Cooperative planning passage with a consequence question.",
    ),
    item(
        "P-008",
        "pilot",
        "formal_comprehension",
        "Summarize what the workshop covers and who should attend.",
        [
            "States that the workshop covers basic record keeping and customer service.",
            "States that it is intended for small business owners and their staff.",
            "Does not promise a certificate or a fee reduction that the notice omits.",
        ],
        "english_reference",
        "The workshop covers basic record keeping and customer service for small business owners and their staff.",
        split="train",
        context=(
            "The business workshop will cover basic record keeping, pricing, and "
            "customer service. It is intended for small business owners and their "
            "staff. The session will run for two hours. Participants should bring "
            "a notebook and a recent sales record if they have one. The notice "
            "does not mention a certificate or a fee reduction."
        ),
        constraints=["Do not add benefits that are not in the notice."],
        secondary=["question_answering"],
        notes="Summary task with an explicit prohibition against unsupported additions.",
    ),
    item(
        "P-009",
        "pilot",
        "formal_comprehension",
        "Explain why the household budget changed and which two costs increased.",
        [
            "States that school transport and food costs increased.",
            "Explains that the family reduced entertainment spending to balance the budget.",
            "Does not claim that income increased.",
        ],
        "english_reference",
        "School transport and food costs increased, so the family reduced entertainment spending to balance the budget. The passage does not say that income increased.",
        split="train",
        context=(
            "The household budget changed this month. School transport costs rose "
            "after the route changed, and food prices increased at the local "
            "market. To balance the budget, the family reduced spending on "
            "entertainment and delayed one planned purchase. Income did not change."
        ),
        constraints=["Mention the two increased costs and the adjustment."],
        response_length="multi_sentence",
        secondary=["question_answering"],
        notes="Budget explanation with an explicit no-income-change constraint.",
    ),
    item(
        "P-010",
        "pilot",
        "formal_comprehension",
        "What does the weather advisory recommend for farmers, and what should travelers expect?",
        [
            "States that farmers should protect seedlings and delay spraying.",
            "States that travelers should expect strong wind and poor visibility.",
            "Does not state that all roads are closed.",
        ],
        "english_reference",
        "Farmers should protect seedlings and delay spraying. Travelers should expect strong wind and poor visibility.",
        split="train",
        context=(
            "The weather advisory predicts strong wind and heavy rain from "
            "Thursday evening. Farmers are advised to protect young seedlings and "
            "to delay spraying until the wind drops. Travelers should expect poor "
            "visibility on exposed roads. The advisory does not say that all roads "
            "will be closed."
        ),
        constraints=["Answer both parts without overstating the advisory."],
        secondary=["question_answering"],
        notes="Weather advisory with a common overstatement as a trap.",
    ),
    item(
        "P-011",
        "pilot",
        "formal_comprehension",
        "According to the refund policy, who can receive a refund and what must the customer provide?",
        [
            "States that a refund is available for unused items returned within fourteen days.",
            "States that the customer must provide the receipt.",
            "Does not claim that used items are refundable.",
        ],
        "english_reference",
        "A customer can receive a refund for unused items returned within fourteen days if the receipt is provided.",
        split="train",
        context=(
            "Unused items may be returned within fourteen days for a refund. The "
            "customer must provide the original receipt. Used items and items "
            "marked as final sale are not refundable. Refunds are paid to the "
            "original payment method. Delivery charges are not refunded unless the "
            "item was damaged on arrival."
        ),
        constraints=["Use the policy, not general assumptions about refunds."],
        secondary=["instruction_following"],
        notes="Policy comprehension with exceptions.",
    ),
    item(
        "P-012",
        "pilot",
        "formal_comprehension",
        "What change does the volunteer schedule introduce, and what should a volunteer do if the new time is impossible?",
        [
            "States that the Saturday shift now starts at eight instead of nine.",
            "States that the volunteer should contact the coordinator before Thursday.",
            "Does not invent a replacement shift.",
        ],
        "english_reference",
        "The Saturday shift now starts at eight instead of nine. A volunteer who cannot attend should contact the coordinator before Thursday.",
        split="train",
        context=(
            "The Saturday volunteer shift will start at eight in the morning "
            "instead of nine, beginning next week. The shift still ends at noon. "
            "Volunteers who cannot attend at the new time should contact the "
            "coordinator before Thursday. The coordinator will discuss options but "
            "cannot promise a replacement shift."
        ),
        constraints=["State the old and new start times."],
        secondary=["question_answering"],
        notes="Schedule change with a clear action.",
    ),
    item(
        "P-013",
        "pilot",
        "formal_comprehension",
        "Summarize the road work notice, including the affected period and the suggested alternative.",
        [
            "States that the market road will be closed for two weeks.",
            "Mentions the suggested alternative route through the school lane.",
            "Does not claim that all shops will close.",
        ],
        "english_reference",
        "The market road will be closed for two weeks for repairs. Drivers are asked to use the school lane as an alternative. Shops will remain open.",
        split="train",
        context=(
            "The market road will be closed for repairs for two weeks, starting "
            "Monday. Drivers should use the school lane as an alternative. The "
            "repair team will work from seven in the morning until five in the "
            "afternoon. Shops along the road will remain open. The notice asks "
            "residents to remove parked vehicles before seven."
        ),
        constraints=["Write a compact summary of the main disruption and detour."],
        response_length="multi_sentence",
        secondary=["question_answering"],
        notes="Public notice summary with a detour.",
    ),
    item(
        "P-014",
        "pilot",
        "formal_comprehension",
        "What concern did the reading group raise, and what did the group decide to do next?",
        [
            "States that members were concerned about the difficulty of the chosen book.",
            "States that the group will choose two shorter texts for the next meeting.",
            "Does not say that the group canceled the reading program.",
        ],
        "english_reference",
        "Members were concerned that the chosen book was too difficult. The group decided to choose two shorter texts for the next meeting.",
        split="train",
        context=(
            "The reading group met on Tuesday. Several members said the chosen "
            "book was difficult to finish within two weeks. Others enjoyed the "
            "discussion but wanted more time. The group decided to choose two "
            "shorter texts for the next meeting and to share notes before the "
            "discussion. No one proposed canceling the group."
        ),
        constraints=["Answer both questions in complete sentences."],
        response_length="multi_sentence",
        secondary=["question_answering"],
        notes="Discussion summary with a decision.",
    ),
    item(
        "P-015",
        "pilot",
        "formal_comprehension",
        "According to the passage, how much does the solar lamp cost?",
        [
            "States that the passage does not provide the price.",
            "Does not guess a price or invent a discount.",
            "Offers to help only if the price is available elsewhere.",
        ],
        "english_reference",
        "The passage does not state how much the solar lamp costs. I cannot give a price from this information.",
        split="validation",
        context=(
            "A local supplier has introduced a solar lamp for households that are "
            "not connected to the electricity grid. The lamp has a small panel and "
            "can charge a phone. The supplier says the lamp is designed for daily "
            "use and includes a one-year repair promise. The notice does not list "
            "a price."
        ),
        constraints=["Do not invent a price."],
        uncertainty="state_uncertainty_if_unanswerable",
        secondary=["question_answering"],
        notes="Unanswerable comprehension item; price is deliberately absent.",
    ),
    item(
        "P-016",
        "pilot",
        "formal_comprehension",
        "How many members does the library have, according to the passage?",
        [
            "States that the passage does not give the number of members.",
            "Does not estimate or invent a membership figure.",
        ],
        "english_reference",
        "The passage does not give the number of library members, so I cannot answer that from the text.",
        split="validation",
        context=(
            "The community library has extended its evening hours. It now closes "
            "at eight in the evening on weekdays. The librarian said the change "
            "was requested by students and workers who cannot visit during the "
            "day. The library will also add two reading tables. The passage does "
            "not mention how many members the library has."
        ),
        constraints=["Use only the passage."],
        uncertainty="state_uncertainty_if_unanswerable",
        secondary=["question_answering"],
        notes="Unanswerable membership count.",
    ),
    item(
        "P-017",
        "pilot",
        "formal_comprehension",
        "In two sentences, summarize the advice about breakfast and explain why the passage says it matters.",
        [
            "Mentions a simple breakfast with a source of energy and a fruit or vegetable.",
            "Explains that breakfast can support attention during morning work or school.",
            "Does not promise a medical outcome or weight change.",
        ],
        "english_reference",
        "The passage recommends a simple breakfast that includes a source of energy and a fruit or vegetable. It says breakfast can support attention during morning work or school, without promising a medical outcome.",
        split="heldout",
        context=(
            "A community health leaflet advises people to eat a simple breakfast "
            "before starting the day. It suggests a source of energy such as "
            "porridge or bread, together with a fruit or vegetable when possible. "
            "The leaflet says a morning meal can help attention during work or "
            "school. It does not promise weight loss or a medical cure. People "
            "with special dietary needs should follow advice from a health worker."
        ),
        constraints=["Write exactly two sentences.", "Do not promise a health outcome."],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Summary and explanation with a medical-overclaim prohibition.",
    ),
    item(
        "P-018",
        "pilot",
        "formal_generation",
        "Write a short formal announcement inviting residents to a community clean-up on Saturday morning.",
        [
            "Includes a clear date, time, and meeting place.",
            "Invites residents to bring gloves or a broom if they can.",
            "Uses a respectful, formal tone and avoids blaming residents.",
        ],
        "english_reference",
        "Residents are invited to a community clean-up on Saturday from eight to eleven in the morning. We will meet at the community hall. Please bring gloves or a broom if you have one. Your participation will help keep our shared spaces clean and safe.",
        split="train",
        constraints=[
            "Use a formal announcement format.",
            "Include a date, time, and meeting place.",
            "Do not shame residents who cannot attend.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Formal public announcement.",
    ),
    item(
        "P-019",
        "pilot",
        "formal_generation",
        "Write a polite formal letter to a landlord asking for a repair to a leaking roof.",
        [
            "Identifies the leaking roof and the room affected.",
            "Requests a repair without making threats.",
            "Offers a practical time for an inspection.",
        ],
        "english_reference",
        "Dear Landlord, I am writing to request a repair to the roof above the back room, which has been leaking since Monday. The leak is affecting the ceiling and floor. Please let me know when someone can inspect it. I am available on Thursday afternoon or Saturday morning. Thank you for your attention to this matter.",
        split="train",
        constraints=[
            "Use a letter format with a greeting and closing.",
            "Keep the tone polite and factual.",
            "Do not threaten legal action.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Formal complaint letter with a restrained tone.",
    ),
    item(
        "P-020",
        "pilot",
        "formal_generation",
        "Explain a savings group to a new member in one clear paragraph.",
        [
            "Explains the purpose of regular contributions.",
            "Mentions that members agree on rules and records.",
            "Avoids promising a fixed profit or guaranteed return.",
        ],
        "english_reference",
        "A savings group helps members set aside money regularly and access small loans from the shared fund. Members agree on the contribution amount, meeting schedule, and rules for borrowing. Records are kept for every payment and loan. The group does not promise a fixed profit; members should understand the rules before joining.",
        split="train",
        constraints=[
            "Write one paragraph.",
            "Do not promise guaranteed profit.",
            "Explain the shared rules and records.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Financial explanation without a guaranteed-return claim.",
    ),
    item(
        "P-021",
        "pilot",
        "formal_generation",
        "Write a short educational paragraph for a community noticeboard about washing hands before eating.",
        [
            "States when hands should be washed.",
            "Mentions soap and clean water.",
            "Uses simple, respectful language and avoids shaming readers.",
        ],
        "english_reference",
        "Washing hands with soap and clean water before eating helps remove dirt and germs. It is especially important after using the toilet, handling waste, or caring for a sick person. Keep soap and water within reach, and teach children the same habit. Small daily actions can protect the health of the whole household.",
        split="train",
        constraints=[
            "Keep the passage short enough for a noticeboard.",
            "Use simple language.",
            "Do not shame readers.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Public-health education text.",
    ),
    item(
        "P-022",
        "pilot",
        "formal_generation",
        "Write a formal notice for a school science fair, including the date, venue, and how students can register.",
        [
            "Includes a date, venue, and registration method.",
            "Invites students to present a project.",
            "Does not invent a prize or a fee.",
        ],
        "english_reference",
        "The school science fair will take place on Friday, the twelfth of next month, in the main hall. Students may register in the office by the fifth of next month. Each project should include a short explanation and a demonstration where possible. Families and teachers are welcome to visit.",
        split="train",
        constraints=[
            "Include a date, venue, and registration method.",
            "Do not mention a prize or fee that is not provided.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="School event notice with explicit omissions.",
    ),
    item(
        "P-023",
        "pilot",
        "formal_generation",
        "Summarize the workplace leave policy in a short formal paragraph for new employees.",
        [
            "Explains that leave should be requested in advance.",
            "Mentions that urgent leave should be reported to the supervisor.",
            "Does not invent a number of leave days.",
        ],
        "english_reference",
        "Employees should request planned leave in advance through the supervisor. For urgent leave, the employee should notify the supervisor as soon as possible and complete the form on return. The policy does not state a fixed number of leave days, so employees should check their contract for the applicable entitlement.",
        split="train",
        constraints=[
            "Write one paragraph.",
            "Do not invent a leave entitlement.",
            "Mention both planned and urgent leave.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Policy summary with an unknown quantity left open.",
    ),
    item(
        "P-024",
        "pilot",
        "formal_generation",
        "Write a short vote of thanks for the end of a community training workshop.",
        [
            "Thanks the facilitators and participants.",
            "Mentions one practical thing participants learned.",
            "Keeps the tone warm but formal.",
        ],
        "english_reference",
        "On behalf of the participants, I thank the facilitators for a well-organized workshop. We appreciated the practical sessions on record keeping and the time given to our questions. I also thank every participant for sharing experience and helping one another. We leave with useful ideas to apply in our work.",
        split="train",
        constraints=[
            "Use a formal spoken style.",
            "Thank both facilitators and participants.",
            "Do not invent names or sponsors.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Formal spoken thanks without invented names.",
    ),
    item(
        "P-025",
        "pilot",
        "formal_generation",
        "Write clear instructions for safe use of a shared workplace kitchen.",
        [
            "Covers cleaning up, storing food, and reporting a fault.",
            "Uses short, direct steps.",
            "Does not blame or name individual staff.",
        ],
        "english_reference",
        "Please clean the surface after preparing food and wash any utensils you use. Store food in a labeled container and remove it from the shared fridge at the end of the week. Report a broken appliance to the office rather than trying to repair it yourself. Keep walkways clear and switch off appliances after use.",
        split="train",
        constraints=[
            "Use short imperative steps.",
            "Cover cleaning, storage, and fault reporting.",
            "Do not name or blame staff.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Workplace procedure with a no-blame constraint.",
    ),
    item(
        "P-026",
        "pilot",
        "formal_generation",
        "Write a paragraph explaining a budget decision to a community group, using the figures provided.",
        [
            "Explains that the group will spend less on events and more on equipment.",
            "Uses the provided figures correctly.",
            "Does not claim that the total budget increased.",
        ],
        "english_reference",
        "The group will reduce the events budget from 400 to 250 and move the difference to equipment, which rises from 300 to 450. The total budget remains 700. This change gives the group better tools for its regular activities while keeping overall spending unchanged.",
        split="train",
        context=(
            "Current budget: events 400, equipment 300, total 700. Proposed budget: "
            "events 250, equipment 450, total 700."
        ),
        constraints=[
            "Use the two figures provided.",
            "State that the total is unchanged.",
            "Do not invent new income.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Budget explanation with arithmetic supplied in the context.",
    ),
    item(
        "P-027",
        "pilot",
        "formal_generation",
        "Write a formal email asking a supplier for an updated price list and delivery time.",
        [
            "States the purpose of the request.",
            "Asks for the price list and delivery time.",
            "Uses a polite closing and does not promise an order.",
        ],
        "english_reference",
        "Dear Supplier, I am writing to request your current price list and the expected delivery time for a small order. We are reviewing our options and would appreciate the information by Friday. Please let me know if you need any details from us. Kind regards, Procurement Office.",
        split="train",
        constraints=[
            "Use an email format.",
            "Ask for both the price list and the delivery time.",
            "Do not promise an order.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Formal procurement email.",
    ),
    item(
        "P-028",
        "pilot",
        "formal_generation",
        "Write a short announcement about a health outreach offering blood pressure checks and general advice.",
        [
            "Includes the service, date, and location.",
            "States that no appointment is required.",
            "Avoids promising a diagnosis or free medicine.",
        ],
        "english_reference",
        "A health outreach will offer blood pressure checks and general health advice on Saturday from nine to one at the community hall. No appointment is required. The team cannot provide a full diagnosis or free medicine, but staff can advise on the next step. Please bring any current medicine list if you have one.",
        split="train",
        constraints=[
            "Include the service, date, and location.",
            "Do not promise a diagnosis or free medicine.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Health outreach notice with limits on claims.",
    ),
    item(
        "P-029",
        "pilot",
        "formal_generation",
        "Write a short essay for a school newsletter explaining why regular reading matters.",
        [
            "Gives at least two reasons reading is useful.",
            "Mentions that reading can be practiced in short sessions.",
            "Avoids claiming that reading guarantees exam success.",
        ],
        "english_reference",
        "Regular reading helps learners build vocabulary, follow ideas, and understand different points of view. It also supports writing because readers see how sentences are organized. Reading does not need to be expensive: a library book, a newspaper, or a short story can be enough. A few minutes each day can become a useful habit, although no single habit guarantees exam success.",
        split="train",
        constraints=[
            "Write a short essay with a clear opening and closing.",
            "Give at least two reasons.",
            "Do not promise exam success.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Short persuasive essay with a no-guarantee constraint.",
    ),
    item(
        "P-030",
        "pilot",
        "formal_generation",
        "Write a formal notice for a library book drive, explaining what is needed and how to donate.",
        [
            "Requests books in good condition.",
            "Explains where and when donations are accepted.",
            "States that textbooks and damaged books cannot be accepted.",
        ],
        "english_reference",
        "The library is collecting books in good condition for its community reading corner. Donations can be brought to the front desk on weekdays between ten and four. We especially welcome storybooks, dictionaries, and recent reference books. We cannot accept damaged books or outdated textbooks. Thank you for helping more readers access useful material.",
        split="validation",
        constraints=[
            "Include what is needed and how to donate.",
            "State what cannot be accepted.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Donation notice with acceptance limits.",
    ),
    item(
        "P-031",
        "pilot",
        "formal_generation",
        "Write a formal apology to customers for a delayed delivery, explaining the next step without making excuses.",
        [
            "Apologizes clearly.",
            "Explains the new delivery window.",
            "Does not blame a named person or promise compensation.",
        ],
        "english_reference",
        "We apologize for the delay to your delivery. The vehicle scheduled for Tuesday was withdrawn for repair, and your order will now arrive on Thursday between nine and twelve. We have not changed the delivery address or the order contents. If this window does not work, please contact the office so we can discuss an alternative. We are sorry for the inconvenience.",
        split="validation",
        constraints=[
            "Use a formal, accountable tone.",
            "Do not promise compensation.",
            "Do not name or blame an employee.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Service apology with an explicit no-compensation limit.",
    ),
    item(
        "P-032",
        "pilot",
        "formal_generation",
        "Explain a new recycling rule to residents in a short formal notice.",
        [
            "Explains how to separate plastic, paper, and food waste.",
            "States the collection day.",
            "Does not claim that all waste can be recycled.",
        ],
        "english_reference",
        "Starting next month, residents are asked to separate plastic, paper, and food waste into different bags. Plastic and paper will be collected on Wednesday morning, and food waste on Friday morning. Please rinse containers and keep paper dry. Items that are not recyclable should go to the usual waste collection point.",
        split="validation",
        constraints=[
            "Explain the three waste groups.",
            "State the collection day.",
            "Do not claim that all waste is recyclable.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Recycling notice with a clear limit.",
    ),
    item(
        "P-033",
        "pilot",
        "formal_generation",
        "Write a formal letter inviting parents to a school meeting about the next term.",
        [
            "Includes the meeting date, time, and venue.",
            "States the main topics.",
            "Asks parents to confirm attendance by a given date.",
        ],
        "english_reference",
        "Dear Parent or Guardian, we invite you to a meeting about the next school term on Thursday, the eighth, at three in the afternoon in the main hall. We will discuss the timetable, textbook arrangements, and the parent volunteer plan. Please confirm attendance at the office by Tuesday. We look forward to meeting you.",
        split="heldout",
        constraints=[
            "Use a letter format.",
            "Include date, time, venue, and a reply deadline.",
            "Do not invent a fee.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="School invitation letter.",
    ),
    item(
        "P-034",
        "pilot",
        "formal_generation",
        "Write a notice explaining a temporary change to a bus route, including the reason and the alternative stop.",
        [
            "States that the route changes because of road repairs.",
            "Names the alternative stop and the start date.",
            "Does not claim that the route is canceled.",
        ],
        "english_reference",
        "From Monday, the town bus will not stop at the market road because of road repairs. Passengers should use the temporary stop behind the community hall. The rest of the route is unchanged. The change will remain in place for two weeks, and notices will be posted at both stops.",
        split="heldout",
        constraints=[
            "State the reason, start date, and alternative stop.",
            "Do not say the route is canceled.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Transport notice with a temporary change.",
    ),
]
