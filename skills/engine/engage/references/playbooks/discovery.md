Nothing is built, branched or committed. The run ends at a recommendation; building one of its
options is a new request from the user.

The run folder is `${user_config.workspace}/.runs/discovery-<slug>/`, `<slug>` naming the question
in a few words.

1. Write the question to `<run folder>/question.md`: what is to be decided and for whom, the
   constraints that hold (the stack, the partners, the regulation, the cost) and what is
   already fixed. Read the rules of the repos the question touches.
2. Learn what exists here: run the **how** skill over the part the work would touch, and search
   GitHub (`gh search code --owner <the repo's owner>`) for a repo of yours that already solves it. When
   nothing here touches it, skip the how and trail what the search covered.
3. Spawn one `geovane:atlas-agent` on sonnet at medium effort per line of research the question
   needs, in parallel, such as:
   - the standards and specs: an RFC, a standard, a provider's docs;
   - how known implementations do it: open-source projects and companies in the market;
   - the failures and incidents known for each approach.

   Give each `question.md` and its line. Each writes `<run folder>/research-<line>.md`, every claim
   beside the URL it comes from, and marks what it inferred.
4. Spawn one `geovane:atlas-agent` on opus at high effort with `question.md`, the how's
   explanation and the research files. It writes `<run folder>/options.md`: at least two options,
   each with how it works, who uses it, what it costs to build, to run and to reverse, how it fits
   the code here and the principles in `../principles.md`, and its risks; then the recommendation,
   its reason, and what would change it.
5. Open the source of each claim the recommendation rests on. Take out of the recommendation
   each claim its source does not support, and mark each claim with no source as inferred.

**Reply:** the recommendation and its reason, the options side by side, the sources the
recommendation rests on, what stays unverified, and the path of `options.md`. Building an option
is a new request that names it.
