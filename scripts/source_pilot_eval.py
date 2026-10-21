"""Proposed 24-item English source evaluation draft, four per capability."""

from source_pilot_common import item

EVALUATION = [
    item(
        "E-001",
        "evaluation",
        "formal_comprehension",
        "According to the notice, when is the tool library open and what must a borrower leave?",
        [
            "States that the tool library is open on Saturday from nine to one.",
            "States that a borrower must leave a contact number.",
            "Does not invent a fee or a membership card.",
        ],
        "english_reference",
        "The tool library is open on Saturday from nine to one. A borrower must leave a contact number.",
        context=(
            "The tool library is open on Saturday from nine in the morning until "
            "one in the afternoon. Borrowers may take one tool at a time. A "
            "borrower must leave a contact number and return the tool by the "
            "following Wednesday. The notice does not mention a fee or a "
            "membership card."
        ),
        constraints=["Use only the notice.", "Answer both parts of the question."],
        secondary=["question_answering"],
        notes="Evaluation item: extraction from a tool-library notice.",
    ),
    item(
        "E-002",
        "evaluation",
        "formal_comprehension",
        "Summarize the main decision in the team note and the reason for it.",
        [
            "States that the team will move the weekly check-in to Wednesday.",
            "Explains that the Monday slot conflicts with the delivery meeting.",
            "Does not include the rejected option as the final decision.",
        ],
        "english_reference",
        "The team will move the weekly check-in to Wednesday because the Monday slot conflicts with the delivery meeting.",
        context=(
            "The team reviewed its weekly check-in time. The Monday slot now "
            "conflicts with the delivery meeting. The team considered Tuesday "
            "afternoon but chose Wednesday morning because more members are "
            "available. The change starts next week. The meeting length stays the "
            "same."
        ),
        constraints=["Write one or two sentences."],
        response_length="multi_sentence",
        secondary=["question_answering"],
        notes="Evaluation item: decision and reason summary.",
    ),
    item(
        "E-003",
        "evaluation",
        "formal_comprehension",
        "How much does the workshop cost?",
        [
            "States that the passage does not give a price.",
            "Does not guess or invent a fee.",
        ],
        "english_reference",
        "The notice does not list a workshop fee. I cannot provide a price from the supplied information.",
        context=(
            "The workshop will cover basic first aid and safety at home. It will "
            "run for three hours at the community center. Participants should wear "
            "comfortable clothing. The notice does not include a fee."
        ),
        constraints=["Do not invent a price."],
        uncertainty="state_uncertainty_if_unanswerable",
        secondary=["question_answering"],
        notes="Evaluation item: unanswerable price question.",
    ),
    item(
        "E-004",
        "evaluation",
        "formal_comprehension",
        "What are the two rules for using the community garden?",
        [
            "States that gardeners must use the shared water tap and keep the path clear.",
            "Does not add a rule about paying a fee.",
        ],
        "english_reference",
        "Gardeners must use the shared water tap and keep the path clear.",
        context=(
            "The community garden is open to households that have registered. "
            "Gardeners must use the shared water tap and keep the path clear for "
            "other users. Tools should be returned to the shed after use. The "
            "notice does not mention a fee."
        ),
        constraints=["List both rules."],
        secondary=["question_answering"],
        notes="Evaluation item: two-rule extraction.",
    ),
    item(
        "E-005",
        "evaluation",
        "formal_generation",
        "Write a formal announcement for a first-aid session, including the date, time, and venue.",
        [
            "Includes a date, time, and venue.",
            "Invites participants to register at the office.",
            "Does not promise a certificate.",
        ],
        "english_reference",
        "A first-aid session will be held on Saturday from nine to eleven in the community hall. Please register at the office before Friday. The session will cover basic home safety and emergency steps.",
        constraints=[
            "Include a date, time, and venue.",
            "Do not promise a certificate.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Evaluation item: formal event announcement.",
    ),
    item(
        "E-006",
        "evaluation",
        "formal_generation",
        "Write a short formal email asking for a copy of the current leave policy.",
        [
            "States the request clearly.",
            "Uses a polite greeting and closing.",
            "Does not invent a deadline for the reply.",
        ],
        "english_reference",
        "Dear Office, I am writing to request a copy of the current leave policy. Please send it to me when convenient. Thank you. Kind regards, Staff Member.",
        constraints=[
            "Use an email format.",
            "Do not invent a reply deadline.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Evaluation item: brief policy request.",
    ),
    item(
        "E-007",
        "evaluation",
        "formal_generation",
        "Explain the new queue system in one short paragraph for visitors.",
        [
            "Explains that visitors take a number and wait for it to be called.",
            "Mentions that urgent cases should speak to the front desk.",
            "Does not promise a maximum waiting time.",
        ],
        "english_reference",
        "Visitors should take a numbered ticket from the machine and wait until the number is called. Urgent cases should speak to the front desk before taking a ticket. The office will serve visitors in number order, but it cannot promise a fixed maximum waiting time.",
        constraints=[
            "Write one paragraph.",
            "Do not promise a maximum waiting time.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Evaluation item: process explanation with a limit.",
    ),
    item(
        "E-008",
        "evaluation",
        "formal_generation",
        "Write a formal letter inviting a guest speaker to a community event without inventing the speaker's name.",
        [
            "Invites the speaker and explains the event topic.",
            "Includes the date, time, and venue.",
            "Uses a formal tone and does not invent a name.",
        ],
        "english_reference",
        "Dear Guest Speaker, we would be grateful if you could speak at our community event. It will be held on Saturday morning at ten in the community hall, and the focus will be practical home safety. We would welcome a short talk and time for questions. Please let us know if you are available. Kind regards, Event Committee.",
        constraints=[
            "Do not invent the speaker's name.",
            "Include a date, time, and venue.",
        ],
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Evaluation item: invitation without invented identity.",
    ),
    item(
        "E-009",
        "evaluation",
        "rewriting_formal_luganda",
        "Rewrite this note in clear, formal Luganda while keeping the room change and the new time.",
        [
            "States the room change and new time.",
            "Removes casual wording.",
            "Does not add a new meeting day.",
        ],
        "english_reference",
        "The meeting has moved to the small room at three in the afternoon. Please use the side entrance.",
        context=(
            "hey, meeting moved to the small room, 3pm now, not the big room. use "
            "the side door. same day."
        ),
        constraints=[
            "Preserve the room and time.",
            "Do not add a new day.",
            "Use a formal register.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Evaluation item: room-change rewrite.",
    ),
    item(
        "E-010",
        "evaluation",
        "rewriting_formal_luganda",
        "Rewrite the following lost-key notice in concise formal Luganda.",
        [
            "States that a key was found near the notice board.",
            "Asks the owner to collect it at the office.",
            "Removes repeated phrases.",
        ],
        "english_reference",
        "A key was found near the notice board. The owner should collect it from the office.",
        context=(
            "a key was found near the notice board. a key was found near the "
            "notice board. if it is your key, come to the office. the office has "
            "the key. please collect the key from the office."
        ),
        constraints=["Remove repetition.", "Do not add a reward."],
        register="mixed",
        secondary=["instruction_following"],
        notes="Evaluation item: redundant lost-item notice.",
    ),
    item(
        "E-011",
        "evaluation",
        "rewriting_formal_luganda",
        "Rewrite the following closing instructions in clear formal Luganda.",
        [
            "States the order of closing steps.",
            "Mentions the lights, the door, and the key.",
            "Does not add a new step.",
        ],
        "english_reference",
        "Switch off the lights, lock the door, and return the key to the office. Check the windows before leaving.",
        context=(
            "when you close, lights off first, then check the windows, lock the "
            "door, and bring the key back to the office. dont forget the windows."
        ),
        constraints=[
            "Keep every step.",
            "Do not add a new step.",
            "Use a clear formal register.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Evaluation item: closing procedure rewrite.",
    ),
    item(
        "E-012",
        "evaluation",
        "rewriting_formal_luganda",
        "Rewrite the following complaint about a late bus in formal, measured Luganda.",
        [
            "States that the bus was late and passengers were not informed.",
            "Asks for a clear update next time.",
            "Avoids insults and threats.",
        ],
        "english_reference",
        "I am writing about the late bus on Tuesday morning. The bus arrived forty minutes late and passengers received no explanation. Please provide a clear update at the stop when a delay occurs.",
        context=(
            "the bus was late again on tuesday, 40 minutes, nobody told us anything. "
            "people were just standing there. this is not good. please tell people "
            "next time when the bus is late."
        ),
        constraints=[
            "Use a formal, measured tone.",
            "Do not insult or threaten anyone.",
            "Ask for a clear update.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Evaluation item: complaint rewrite.",
    ),
    item(
        "E-013",
        "evaluation",
        "question_answering",
        "What time does the office close on Friday?",
        [
            "States that the office closes at three on Friday.",
            "Does not give the weekday closing time.",
        ],
        "english_reference",
        "The office closes at three in the afternoon on Friday.",
        context=(
            "The office is open from eight to five on Monday to Thursday. On "
            "Friday it closes at three in the afternoon. The office is closed on "
            "public holidays."
        ),
        constraints=["Answer only the Friday time."],
        secondary=["formal_comprehension"],
        notes="Evaluation item: answerable closing-time question.",
    ),
    item(
        "E-014",
        "evaluation",
        "question_answering",
        "How many staff work in the office?",
        [
            "States that the passage does not give a staff count.",
            "Does not estimate or invent a number.",
        ],
        "english_reference",
        "The passage does not state how many staff work in the office, so I cannot answer that.",
        context=(
            "The office handles permits, payments, and records. It is open from "
            "eight to five on weekdays. Visitors should take a numbered ticket. "
            "The passage does not give a staff count."
        ),
        constraints=["Do not estimate."],
        uncertainty="state_uncertainty_if_unanswerable",
        secondary=["formal_comprehension"],
        notes="Evaluation item: unanswerable staff count.",
    ),
    item(
        "E-015",
        "evaluation",
        "question_answering",
        "Which day is the meeting?",
        [
            "Notes that the message mentions two meetings.",
            "Asks which meeting the user means.",
            "Does not choose a day without confirmation.",
        ],
        "english_reference",
        "The message mentions a budget meeting on Tuesday and a staff meeting on Thursday. Which one do you mean?",
        context=(
            "The budget meeting is on Tuesday at nine. The staff meeting is on "
            "Thursday at two. Both are in the main office. The budget meeting is "
            "for team leads only."
        ),
        constraints=["Ask one clarifying question."],
        uncertainty="ask_clarifying_question_if_ambiguous",
        secondary=["formal_comprehension"],
        notes="Evaluation item: ambiguous meeting reference.",
    ),
    item(
        "E-016",
        "evaluation",
        "question_answering",
        "What should a visitor bring to the registration desk?",
        [
            "States that the visitor should bring an identity document and the appointment letter.",
            "Does not add a fee.",
        ],
        "english_reference",
        "A visitor should bring an identity document and the appointment letter to the registration desk.",
        context=(
            "Visitors should report to the registration desk before entering the "
            "building. Bring an identity document and the appointment letter. "
            "Bags may be checked at the entrance. The notice does not mention a "
            "fee."
        ),
        constraints=["Answer from the notice only."],
        secondary=["formal_comprehension"],
        notes="Evaluation item: answerable preparation question.",
    ),
    item(
        "E-017",
        "evaluation",
        "instruction_following",
        "Write exactly two sentences in Luganda announcing the changed opening time. Include the word Monday and do not mention a fee.",
        [
            "Uses exactly two sentences.",
            "Includes the word Monday.",
            "Responds in Luganda.",
            "Does not mention a fee.",
        ],
        "english_reference",
        "The office will open at nine instead of eight starting on Monday. Please check the notice board for any further change.",
        context=(
            "The office will open at nine instead of eight starting Monday. The "
            "closing time is unchanged. No fee is involved in the schedule change."
        ),
        constraints=[
            "Use exactly two sentences.",
            "Include the word Monday.",
            "Do not mention a fee.",
            "Respond in Luganda.",
        ],
        response_length="multi_sentence",
        secondary=["formal_generation"],
        notes="Evaluation item: two-sentence constrained notice.",
    ),
    item(
        "E-018",
        "evaluation",
        "instruction_following",
        "Give three short bullet points for preparing a shared room for a meeting. Use no more than fifty words and include two actions.",
        [
            "Provides exactly three bullet points.",
            "Includes two concrete actions.",
            "Stays within fifty words.",
        ],
        "english_reference",
        "- Arrange the chairs around the table.\n- Check that the room has water.\n- Leave the door unlocked for the facilitator.",
        constraints=[
            "Use exactly three bullet points.",
            "Use no more than fifty words.",
            "Include two actions.",
        ],
        response_length="multi_sentence",
        secondary=["formal_generation"],
        notes="Evaluation item: constrained preparation list.",
    ),
    item(
        "E-019",
        "evaluation",
        "instruction_following",
        "Write a three-line packing list for a one-day training. Use exactly three items and no more than twenty words. Do not include food.",
        [
            "Provides exactly three lines with three items.",
            "Does not include food.",
            "Stays within twenty words.",
        ],
        "english_reference",
        "Notebook\nIdentity document\nPen",
        constraints=[
            "Use exactly three lines.",
            "Use no more than twenty words.",
            "Do not include food.",
        ],
        response_length="multi_sentence",
        secondary=["formal_generation"],
        notes="Evaluation item: constrained packing list.",
    ),
    item(
        "E-020",
        "evaluation",
        "instruction_following",
        "Write a short notice with a heading and one paragraph. Include the venue and one action, and do not invent a phone number.",
        [
            "Has a heading and one paragraph.",
            "Includes the venue and one action.",
            "Does not invent a phone number.",
        ],
        "english_reference",
        "Community Clean-Up\n\nJoin the community clean-up at the market square on Saturday at eight in the morning. Please bring gloves if you have them.",
        constraints=[
            "Use a heading and one paragraph.",
            "Include the venue and one action.",
            "Do not invent a phone number.",
        ],
        response_length="multi_sentence",
        secondary=["formal_generation"],
        notes="Evaluation item: structured short notice.",
    ),
    item(
        "E-021",
        "evaluation",
        "short_conversation",
        "The date changed, right? Which day should I write in my calendar now?",
        [
            "Confirms the new date.",
            "Uses the earlier correction.",
        ],
        "english_reference",
        "Write Friday in your calendar. The event moved from Wednesday to Friday.",
        turns=[
            {"role": "user", "content": "Is the event on Wednesday?"},
            {
                "role": "assistant",
                "content": "The event was originally on Wednesday, but it has moved to Friday.",
            },
        ],
        constraints=["Use the corrected date."],
        requires_prior_context=True,
        response_length="multi_sentence",
        secondary=["question_answering"],
        notes="Evaluation item: date correction follow-up.",
    ),
    item(
        "E-022",
        "evaluation",
        "short_conversation",
        "Which office is that again? I need to return the form today.",
        [
            "Names the records office.",
            "Refers to the earlier office detail.",
        ],
        "english_reference",
        "The records office is on the ground floor. That is where you should return the form.",
        turns=[
            {
                "role": "user",
                "content": "Where should I return the completed form?",
            },
            {
                "role": "assistant",
                "content": "Return it to the records office on the ground floor.",
            },
            {"role": "user", "content": "Is that the same office that handles payments?"},
            {
                "role": "assistant",
                "content": "No, payments are handled by the finance office.",
            },
        ],
        constraints=["Name the correct office."],
        requires_prior_context=True,
        response_length="multi_sentence",
        secondary=["question_answering"],
        notes="Evaluation item: office reference across turns.",
    ),
    item(
        "E-023",
        "evaluation",
        "short_conversation",
        "Can you give me the reference number so I can follow up?",
        [
            "States that the reference number is not available in the conversation.",
            "Suggests contacting the records desk.",
            "Does not invent a reference number.",
        ],
        "english_reference",
        "I do not have the reference number in this conversation. Please contact the records desk and ask them to look it up.",
        turns=[
            {
                "role": "user",
                "content": "I handed in the application on Monday.",
            },
            {
                "role": "assistant",
                "content": "The records desk received an application on Monday.",
            },
        ],
        constraints=["Do not invent a reference number."],
        uncertainty="state_uncertainty_if_unanswerable",
        requires_prior_context=True,
        response_length="multi_sentence",
        secondary=["question_answering"],
        notes="Evaluation item: unavailable application reference.",
    ),
    item(
        "E-024",
        "evaluation",
        "short_conversation",
        "Can I send a copy of the letter instead of the original?",
        [
            "States that the original is required.",
            "Does not accept a copy.",
        ],
        "english_reference",
        "The original letter is required. A copy is not accepted.",
        turns=[
            {"role": "user", "content": "What should I bring for the appointment?"},
            {
                "role": "assistant",
                "content": "Bring the appointment letter and an identity document.",
            },
        ],
        constraints=["Answer the copy question directly."],
        requires_prior_context=True,
        response_length="multi_sentence",
        secondary=["question_answering"],
        notes="Evaluation item: original-versus-copy follow-up.",
    ),
]
