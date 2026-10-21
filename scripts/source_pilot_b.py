"""English source examples for rewriting and question answering."""

from source_pilot_common import item

PILOT = [
    item(
        "P-035",
        "pilot",
        "rewriting_formal_luganda",
        "Rewrite the following note in formal, clear Luganda. Preserve the meaning and do not add new details.",
        [
            "Keeps the meeting day and time.",
            "Removes the casual wording and repeated phrases.",
            "Does not add an agenda item or a different venue.",
        ],
        "english_reference",
        "The staff meeting will take place on Wednesday at two in the afternoon in the main office. Please bring the progress notes.",
        split="train",
        context=(
            "hey team, the meeting is wednesday at 2, same place as usual, the main "
            "office. pls bring the progress notes. dont forget, 2 o'clock, main office."
        ),
        constraints=[
            "Preserve the day, time, and place.",
            "Do not add new information.",
            "Use a formal register.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Informal staff note with redundancy.",
    ),
    item(
        "P-036",
        "pilot",
        "rewriting_formal_luganda",
        "Rewrite the following instructions in formal, clear Luganda so that a new volunteer can follow them.",
        [
            "States that the key should be collected from the office.",
            "States that the room should be locked after use.",
            "Orders the steps clearly without changing their meaning.",
        ],
        "english_reference",
        "Collect the room key from the office before the session. After the session, switch off the lights and lock the door. Return the key to the office the same day.",
        split="train",
        context=(
            "get the key from the office before you start. when you finish, switch "
            "off the lights and lock the room. bring the key back to the office "
            "the same day. if the office is closed, leave the key with the person "
            "at the front desk."
        ),
        constraints=[
            "Keep every instruction.",
            "Use a formal register.",
            "Arrange the steps clearly.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Unclear volunteer instructions requiring ordering.",
    ),
    item(
        "P-037",
        "pilot",
        "rewriting_formal_luganda",
        "Rewrite the following announcement in formal, concise Luganda. Remove repetition without losing the request.",
        [
            "States that the blue folder was left in the reading room.",
            "Asks the person who found it to leave it at the front desk.",
            "Does not include the repeated phrases from the original.",
        ],
        "english_reference",
        "A blue folder was left in the reading room. Anyone who finds it should leave it at the front desk.",
        split="train",
        context=(
            "A blue folder was left in the reading room. It is a blue folder and "
            "it was left in the reading room. If you find the blue folder, please "
            "leave the blue folder at the front desk. Please leave it at the front "
            "desk if you find it."
        ),
        constraints=[
            "Remove redundancy.",
            "Preserve the lost item and where to return it.",
            "Do not add a reward.",
        ],
        register="mixed",
        secondary=["instruction_following"],
        notes="Redundant notice with a clear request.",
    ),
    item(
        "P-038",
        "pilot",
        "rewriting_formal_luganda",
        "Rewrite the following customer message in formal, consistent Luganda.",
        [
            "States the problem with the delayed order.",
            "Asks for a new delivery date.",
            "Uses one consistent formal register.",
        ],
        "english_reference",
        "I am writing about my order, which was due on Monday and has not arrived. Please confirm the new delivery date and let me know if the address is still correct.",
        split="train",
        context=(
            "hi, my order was supposed to come monday but nothing came. honestly "
            "this is frustrating. can you tell me when it will come now? also, "
            "please confirm that you still have the right address. thanks."
        ),
        constraints=[
            "Keep the complaint factual.",
            "Do not insult the supplier.",
            "Ask for the new date and address confirmation.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Mixed-register customer complaint.",
    ),
    item(
        "P-039",
        "pilot",
        "rewriting_formal_luganda",
        "Rewrite the following message as a polite formal request to a landlord in Luganda.",
        [
            "Identifies the broken window and the room.",
            "Requests a repair without threats.",
            "Preserves the offer to be available for an inspection.",
        ],
        "english_reference",
        "I am writing to ask you to repair the broken window in the front room. The window no longer closes properly. I am available for an inspection on Friday afternoon. Thank you for your help.",
        split="train",
        context=(
            "the window in the front room is broken and it wont close. can you "
            "please fix it? im around friday afternoon if someone needs to look at "
            "it. thanks."
        ),
        constraints=[
            "Use a formal letter style.",
            "Do not threaten the landlord.",
            "Keep the inspection offer.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Informal repair request turned into a polite letter.",
    ),
    item(
        "P-040",
        "pilot",
        "rewriting_formal_luganda",
        "Turn the following notes into a clear formal paragraph in Luganda.",
        [
            "Explains that the trip leaves at seven and returns at five.",
            "Mentions the meeting point and the need to carry water.",
            "Does not add a cost or a different destination.",
        ],
        "english_reference",
        "The group will leave for the field visit at seven in the morning and return at five in the afternoon. Everyone should meet at the main gate and carry drinking water. The destination and the departure time are unchanged.",
        split="train",
        context=(
            "trip leaves 7am, back 5pm. meet at main gate. bring water. same place "
            "as before. dont be late. no cost mentioned."
        ),
        constraints=[
            "Write one connected paragraph.",
            "Keep the times and meeting point.",
            "Do not invent a fee.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Bullet-like notes with an omitted cost.",
    ),
    item(
        "P-041",
        "pilot",
        "rewriting_formal_luganda",
        "Rewrite the following apology in formal, accountable Luganda.",
        [
            "Apologizes for the missed appointment.",
            "Explains that the office will call to reschedule.",
            "Avoids blaming traffic or another person.",
        ],
        "english_reference",
        "I apologize for missing our appointment on Tuesday. The office will call you to arrange a new time. I am sorry for the inconvenience and will confirm the new appointment in writing.",
        split="train",
        context=(
            "sorry i missed our meeting on tuesday. things got messy. the office "
            "will call you to find another time. sorry again, i will confirm it in "
            "writing."
        ),
        constraints=[
            "Use a formal apology.",
            "Do not blame traffic or another person.",
            "Mention the rescheduling step.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Informal apology without excuses.",
    ),
    item(
        "P-042",
        "pilot",
        "rewriting_formal_luganda",
        "Rewrite the following policy note as a clear formal statement in Luganda.",
        [
            "States that requests need two working days.",
            "Explains that urgent requests should be marked urgent.",
            "Does not promise same-day approval.",
        ],
        "english_reference",
        "Requests should be submitted at least two working days before the needed date. Urgent requests should be marked clearly and explained. The office will review each request, but same-day approval is not guaranteed.",
        split="train",
        context=(
            "send requests two working days before. if its urgent mark it urgent "
            "and explain why. we will look at it but dont assume it will be done "
            "same day."
        ),
        constraints=[
            "Preserve the two-day rule.",
            "Do not promise same-day approval.",
            "Use a formal register.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Policy note with an important limit.",
    ),
    item(
        "P-043",
        "pilot",
        "rewriting_formal_luganda",
        "Rewrite the following event invitation in formal, concise Luganda.",
        [
            "Includes the event, date, time, and venue.",
            "Removes repeated phrases.",
            "Does not add a fee or a guest speaker.",
        ],
        "english_reference",
        "You are invited to a community discussion on Saturday at ten in the morning at the community hall. The discussion will focus on the new water schedule. Please arrive on time.",
        split="train",
        context=(
            "you are invited to a community discussion. the discussion is on "
            "saturday. it starts at 10am. it is at the community hall. we will "
            "talk about the new water schedule. please come on time. community "
            "discussion, saturday, 10am, community hall."
        ),
        constraints=[
            "Include the event, date, time, and venue.",
            "Remove repetition.",
            "Do not add a fee or speaker.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Repetitive invitation.",
    ),
    item(
        "P-044",
        "pilot",
        "rewriting_formal_luganda",
        "Rewrite the following staff message in formal, consistent Luganda.",
        [
            "States that the deadline moved to Friday.",
            "Explains that the form should be sent to the office.",
            "Does not change the deadline or the recipient.",
        ],
        "english_reference",
        "The deadline for the form has moved to Friday. Please send the completed form to the office by the end of that day. The recipient and the required information are unchanged.",
        split="train",
        context=(
            "ok so the form deadline is now friday, not thursday. send it to the "
            "office when its done. the office is still the same. please send the "
            "form to the office by friday. thanks."
        ),
        constraints=[
            "State the new deadline.",
            "Keep the recipient unchanged.",
            "Use one formal register.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Mixed-register deadline message.",
    ),
    item(
        "P-045",
        "pilot",
        "rewriting_formal_luganda",
        "Rewrite the following reminder in formal Luganda.",
        [
            "Reminds the reader to submit the report.",
            "Keeps the deadline and the recipient.",
            "Does not add a penalty.",
        ],
        "english_reference",
        "This is a reminder to submit the monthly report to the program office by Friday at noon. Please contact the office if you need help before the deadline.",
        split="train",
        context=(
            "just a reminder, the monthly report is due friday at noon. send it to "
            "the program office. if you need help, ask before friday. no penalty "
            "mentioned."
        ),
        constraints=[
            "Keep the deadline and recipient.",
            "Do not add a penalty.",
            "Use a formal reminder tone.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Informal reminder with a no-penalty constraint.",
    ),
    item(
        "P-046",
        "pilot",
        "rewriting_formal_luganda",
        "Rewrite the following community notice in clear formal Luganda.",
        [
            "Explains that the water will be off on Tuesday.",
            "States the repair time and the collection point.",
            "Does not claim that the outage will last all week.",
        ],
        "english_reference",
        "Water will be unavailable on Tuesday from nine in the morning until three in the afternoon while the main pipe is repaired. Households may collect water from the community tank near the market. Normal service is expected to return on Tuesday evening.",
        split="train",
        context=(
            "water off tuesday 9 to 3. pipe repair. get water from the tank near "
            "the market. should be back tuesday evening. not all week."
        ),
        constraints=[
            "State the outage day and hours.",
            "Do not exaggerate the duration.",
            "Mention the collection point.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Short utility notice with a duration limit.",
    ),
    item(
        "P-047",
        "pilot",
        "rewriting_formal_luganda",
        "Rewrite the following complaint about noise in formal, measured Luganda.",
        [
            "Identifies the repeated late-night noise.",
            "Asks for a quiet period after ten.",
            "Avoids insults or threats.",
        ],
        "english_reference",
        "I am writing to raise a concern about repeated late-night noise from the shared courtyard. The noise has continued after ten on several weeknights. I request that the courtyard be kept quiet after ten so that residents can rest. I would welcome a short meeting to discuss a workable arrangement.",
        split="validation",
        context=(
            "the noise in the courtyard is too much. its every night after 10 and "
            "people cant sleep. please tell them to stop. someone needs to fix "
            "this."
        ),
        constraints=[
            "Use a measured formal tone.",
            "Do not insult or threaten anyone.",
            "Ask for a practical solution.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Emotional complaint rewritten as a measured request.",
    ),
    item(
        "P-048",
        "pilot",
        "rewriting_formal_luganda",
        "Turn the following meeting notes into a formal summary in Luganda.",
        [
            "States the two decisions about the schedule and the notice board.",
            "Mentions who will act and by when.",
            "Does not include side comments or blame.",
        ],
        "english_reference",
        "The group agreed to move the weekly meeting to Thursday at four and to place a notice on the board by Monday. The secretary will prepare the notice, and the chair will confirm the room. Side comments about attendance were not recorded as decisions.",
        split="validation",
        context=(
            "meeting notes: move weekly meeting to thurs 4pm. put notice on board "
            "by monday. secretary writes notice. chair checks room. some people "
            "came late, mentioned but not a decision. side comments not needed."
        ),
        constraints=[
            "Record only decisions and actions.",
            "Do not include side comments.",
            "Keep the people and deadlines.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Notes-to-summary task with a no-side-comments rule.",
    ),
    item(
        "P-049",
        "pilot",
        "rewriting_formal_luganda",
        "Rewrite the following invitation in formal Luganda, keeping it warm but concise.",
        [
            "Invites the reader to the launch event.",
            "Includes the date, time, and place.",
            "Does not promise food or transport.",
        ],
        "english_reference",
        "You are warmly invited to the launch of the community reading corner on Saturday at eleven in the morning at the library. The event will include a short introduction and time to browse the new books. We look forward to welcoming you.",
        split="heldout",
        context=(
            "come to our launch! its saturday at 11 at the library. we are opening "
            "the new reading corner. short intro then look at the books. hope you "
            "can make it. no food or transport promised."
        ),
        constraints=[
            "Keep a warm but formal tone.",
            "Include the date, time, and place.",
            "Do not promise food or transport.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Informal launch invitation.",
    ),
    item(
        "P-050",
        "pilot",
        "rewriting_formal_luganda",
        "Rewrite the following instructions for completing a form in clear formal Luganda.",
        [
            "States that the form should be completed in block letters.",
            "Explains that the original should be submitted, not a photograph.",
            "Keeps the office and deadline.",
        ],
        "english_reference",
        "Please complete the form in block letters and submit the original to the records office by Friday. Do not submit a photograph or a copy. The office can help with any question before the deadline.",
        split="heldout",
        context=(
            "fill the form in block letters. send the original to records office by "
            "friday. dont send a photo or copy. ask the office if you need help "
            "before friday."
        ),
        constraints=[
            "Keep the block-letter rule.",
            "Keep the original-copy rule and the deadline.",
            "Use a formal register.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Form instructions with a copy prohibition.",
    ),
    item(
        "P-051",
        "pilot",
        "rewriting_formal_luganda",
        "Rewrite the following schedule announcement in concise formal Luganda.",
        [
            "States the new opening time and the start date.",
            "Removes repetition.",
            "Does not claim that the service is open all night.",
        ],
        "english_reference",
        "From Monday, the service will open at eight in the morning instead of seven. The closing time remains five in the afternoon. The change is temporary while the front desk is repaired.",
        split="heldout",
        context=(
            "new opening time 8am starting monday. closing still 5pm. its temporary "
            "because the front desk is being repaired. not open all night. opening "
            "at 8, not 7. monday start."
        ),
        constraints=[
            "State the old and new opening times.",
            "Do not claim all-night service.",
            "Remove repetition.",
        ],
        register="mixed",
        response_length="multi_sentence",
        secondary=["instruction_following"],
        notes="Repetitive schedule change.",
    ),
    item(
        "P-052",
        "pilot",
        "question_answering",
        "When does the community meeting start, and where will it be held?",
        [
            "States that the meeting starts at four in the afternoon.",
            "States that it will be held in the community hall.",
        ],
        "english_reference",
        "The community meeting starts at four in the afternoon in the community hall.",
        split="train",
        context=(
            "Notice: The community meeting will be held on Thursday at four in the "
            "afternoon in the community hall. The meeting will discuss the new "
            "water schedule. Please arrive ten minutes early."
        ),
        constraints=["Give both the time and the place."],
        secondary=["formal_comprehension"],
        notes="Answerable question with two facts.",
    ),
    item(
        "P-053",
        "pilot",
        "question_answering",
        "What should a person do to renew a trading permit, according to the office note?",
        [
            "States that the application form and old permit are required.",
            "States that the fee is paid at the cash desk.",
            "Does not add a different office or deadline.",
        ],
        "english_reference",
        "To renew a trading permit, submit the application form and the old permit, then pay the fee at the cash desk. The office note does not mention a different office.",
        split="train",
        context=(
            "Office note: Bring the completed application form and the old trading "
            "permit to the records desk. Pay the renewal fee at the cash desk. "
            "Keep the receipt. The permit will be ready after three working days."
        ),
        constraints=["Follow the order in the office note."],
        secondary=["formal_comprehension"],
        notes="Procedural answer with an explicit order.",
    ),
    item(
        "P-054",
        "pilot",
        "question_answering",
        "How much is the renewal fee?",
        [
            "States that the note does not give the amount.",
            "Does not guess or invent a fee.",
        ],
        "english_reference",
        "The office note does not give the renewal fee, so I cannot state the amount from this information.",
        split="train",
        context=(
            "At the records desk, applicants should hand in the completed form "
            "together with the old permit. Payment is made at the cash desk, and "
            "the receipt should be kept. The permit is normally ready after three "
            "working days. No fee amount is printed here."
        ),
        constraints=["Do not invent an amount."],
        uncertainty="state_uncertainty_if_unanswerable",
        secondary=["formal_comprehension"],
        notes="Unanswerable fee question.",
    ),
    item(
        "P-055",
        "pilot",
        "question_answering",
        "When is the event?",
        [
            "Notes that two dates appear in the message.",
            "Asks which event the user means.",
            "Does not choose one date without confirmation.",
        ],
        "english_reference",
        "The message mentions a planning meeting on Tuesday and a public event on Saturday. Which event do you mean?",
        split="train",
        context=(
            "The planning meeting is on Tuesday at ten. The public event is on "
            "Saturday at two. Both will be held in the community hall. Volunteers "
            "should arrive one hour early for the public event."
        ),
        constraints=["Ask one clarifying question."],
        uncertainty="ask_clarifying_question_if_ambiguous",
        secondary=["formal_comprehension"],
        notes="Ambiguous event reference.",
    ),
    item(
        "P-056",
        "pilot",
        "question_answering",
        "Who is the coordinator of the program?",
        [
            "States that the passage does not name the coordinator.",
            "Does not invent a name.",
        ],
        "english_reference",
        "The passage does not name the program coordinator, so I cannot identify that person from the text.",
        split="train",
        context=(
            "The youth program will run for six weeks. Sessions will be held on "
            "weekday afternoons. The program coordinator will contact participants "
            "before the first session. The notice does not include the coordinator's "
            "name or phone number."
        ),
        constraints=["Do not invent a name."],
        uncertainty="state_uncertainty_if_unanswerable",
        secondary=["formal_comprehension"],
        notes="Unanswerable identity question.",
    ),
    item(
        "P-057",
        "pilot",
        "question_answering",
        "Which office should I visit?",
        [
            "Notes that the message names two offices.",
            "Asks what the user needs help with.",
            "Does not choose an office without knowing the task.",
        ],
        "english_reference",
        "The message names the records office for permits and the finance office for payments. What do you need help with?",
        split="train",
        context=(
            "Records office: permits, applications, and letters. Finance office: "
            "payments, receipts, and refunds. Both offices are on the ground floor. "
            "The records office closes at four, and the finance office closes at "
            "three thirty."
        ),
        constraints=["Ask a clarifying question before directing the user."],
        uncertainty="ask_clarifying_question_if_ambiguous",
        secondary=["formal_comprehension"],
        notes="Ambiguous office choice.",
    ),
    item(
        "P-058",
        "pilot",
        "question_answering",
        "Which plan costs less over three months, and by how much?",
        [
            "States that the monthly plan costs less overall.",
            "Calculates the three-month totals correctly.",
            "Does not claim that the annual plan is cheaper.",
        ],
        "english_reference",
        "The monthly plan costs 30 for three months, while the quarterly plan costs 36, so the monthly plan costs 6 less.",
        split="train",
        context=(
            "Plan A: pay 10 each month. Plan B: pay 36 every three months. Both "
            "plans include the same service. There is no joining fee."
        ),
        constraints=["Show the comparison in the answer."],
        response_length="multi_sentence",
        secondary=["formal_comprehension"],
        notes="Simple arithmetic comparison supplied in context.",
    ),
    item(
        "P-059",
        "pilot",
        "question_answering",
        "Will it rain tomorrow?",
        [
            "States that the message does not provide a forecast.",
            "Does not guess the weather.",
        ],
        "english_reference",
        "The message does not provide a weather forecast, so I cannot say whether it will rain tomorrow.",
        split="train",
        context=(
            "The outdoor market will open at seven tomorrow. Vendors should arrive "
            "early to set up. The organizers will provide drinking water. The "
            "message does not include a weather forecast."
        ),
        constraints=["Do not guess."],
        uncertainty="state_uncertainty_if_unanswerable",
        secondary=["formal_comprehension"],
        notes="Unanswerable weather question.",
    ),
    item(
        "P-060",
        "pilot",
        "question_answering",
        "Can I bring a friend to the workshop?",
        [
            "States that the notice does not say whether guests are allowed.",
            "Offers to check with the organizer.",
            "Does not assume that a friend may attend.",
        ],
        "english_reference",
        "The notice does not say whether guests may attend. Are you asking about one friend or a group?",
        split="train",
        context=(
            "The workshop is open to registered participants. Please bring your "
            "registration number and a notebook. The room has limited seating. "
            "The notice does not mention guests."
        ),
        constraints=["Do not assume that guests are allowed."],
        uncertainty="ask_clarifying_question_if_ambiguous",
        secondary=["formal_comprehension"],
        notes="Ambiguous guest policy.",
    ),
    item(
        "P-061",
        "pilot",
        "question_answering",
        "Why was the delivery delayed?",
        [
            "States that the vehicle was withdrawn for repair.",
            "Mentions the new delivery day.",
        ],
        "english_reference",
        "The delivery was delayed because the vehicle was withdrawn for repair. The new delivery day is Thursday.",
        split="train",
        context=(
            "The delivery did not arrive on Tuesday because the vehicle was taken "
            "for repair. The order is now expected on Thursday, between nine in "
            "the morning and noon."
        ),
        constraints=["Answer both the reason and the new day."],
        secondary=["formal_comprehension"],
        notes="Answerable cause question.",
    ),
    item(
        "P-062",
        "pilot",
        "question_answering",
        "How many people attended the meeting?",
        [
            "States that the notes do not give an attendance count.",
            "Does not estimate a number.",
        ],
        "english_reference",
        "The notes do not give an attendance count, so I cannot state how many people attended.",
        split="train",
        context=(
            "The community meeting discussed the new water schedule. Members asked "
            "about repair costs and the timetable for the work. The chair thanked "
            "everyone who attended. The notes do not record the number of people "
            "present."
        ),
        constraints=["Do not estimate."],
        uncertainty="state_uncertainty_if_unanswerable",
        secondary=["formal_comprehension"],
        notes="Unanswerable attendance count.",
    ),
    item(
        "P-063",
        "pilot",
        "question_answering",
        "Is the ten o'clock session full?",
        [
            "States that the notice does not give capacity or remaining places.",
            "Suggests contacting the office to confirm.",
            "Does not claim that the session is full or open.",
        ],
        "english_reference",
        "The notice does not say whether the ten o'clock session is full. Please contact the office to confirm available places.",
        split="train",
        context=(
            "Sessions are held at nine, ten, and eleven in the morning. "
            "Registration is required. Participants should arrive fifteen minutes "
            "early. The notice does not mention the number of places in each "
            "session."
        ),
        constraints=["Do not guess the capacity."],
        uncertainty="state_uncertainty_if_unanswerable",
        secondary=["formal_comprehension"],
        notes="Ambiguous capacity question.",
    ),
    item(
        "P-064",
        "pilot",
        "question_answering",
        "What should I bring to the first training session?",
        [
            "States that the participant should bring a notebook and an identity document.",
            "Does not add a laptop or a fee.",
        ],
        "english_reference",
        "Bring a notebook and an identity document to the first training session. The notice does not require a laptop or a fee.",
        split="validation",
        context=(
            "The first training session will start at nine in the morning. Bring a "
            "notebook and one identity document for registration. The session will "
            "end at noon. A short break will be provided. No laptop is required."
        ),
        constraints=["Answer only from the notice."],
        secondary=["formal_comprehension"],
        notes="Answerable preparation question.",
    ),
    item(
        "P-065",
        "pilot",
        "question_answering",
        "What is the phone number of the organizer?",
        [
            "States that the message does not give a phone number.",
            "Does not invent contact details.",
        ],
        "english_reference",
        "The message does not include the organizer's phone number, so I cannot provide it.",
        split="validation",
        context=(
            "The community sports day will take place on Saturday at the main "
            "field. Teams should register at the gate before eight. The organizer "
            "will share final instructions at the field. The message does not list "
            "a phone number."
        ),
        constraints=["Do not invent contact details."],
        uncertainty="state_uncertainty_if_unanswerable",
        secondary=["formal_comprehension"],
        notes="Unanswerable contact question.",
    ),
    item(
        "P-066",
        "pilot",
        "question_answering",
        "Which training is better for me?",
        [
            "States that the message does not describe the user's needs.",
            "Asks what the user wants to learn or how much time is available.",
            "Does not recommend one option without that information.",
        ],
        "english_reference",
        "The message does not say what you want to learn or how much time you have, so I cannot choose for you. What skill are you hoping to build?",
        split="validation",
        context=(
            "Two trainings are available. The morning training covers basic "
            "record keeping and runs for two hours. The evening training covers "
            "customer service and runs for four hours over two evenings. Both are "
            "open to beginners."
        ),
        constraints=["Ask for the missing decision criteria."],
        uncertainty="ask_clarifying_question_if_ambiguous",
        secondary=["formal_comprehension"],
        notes="Ambiguous recommendation request.",
    ),
    item(
        "P-067",
        "pilot",
        "question_answering",
        "Who is eligible for the small business grant?",
        [
            "States that the applicant must have a registered business and a simple business plan.",
            "Mentions that the business must have operated for at least six months.",
            "Does not add an age limit or a membership requirement.",
        ],
        "english_reference",
        "An applicant is eligible if the business is registered, has operated for at least six months, and has a simple business plan. The notice does not mention an age limit or a membership requirement.",
        split="heldout",
        context=(
            "The small business grant is open to registered businesses that have "
            "operated for at least six months. Applicants should submit a simple "
            "business plan and a recent record of sales. The grant does not require "
            "membership in a trade association. The notice does not mention an age "
            "limit."
        ),
        constraints=["List every eligibility condition in the notice."],
        response_length="multi_sentence",
        secondary=["formal_comprehension"],
        notes="Eligibility question with two absent conditions.",
    ),
    item(
        "P-068",
        "pilot",
        "question_answering",
        "What is the price of the training?",
        [
            "States that the message does not give a price.",
            "Does not invent a fee or a discount.",
        ],
        "english_reference",
        "The message does not state the price of the training, so I cannot give an amount.",
        split="heldout",
        context=(
            "The training will cover basic bookkeeping and customer care. It will "
            "run for two days at the community center. Participants should bring a "
            "notebook. The message does not mention a price or a discount."
        ),
        constraints=["Do not invent a price."],
        uncertainty="state_uncertainty_if_unanswerable",
        secondary=["formal_comprehension"],
        notes="Unanswerable training price.",
    ),
]
